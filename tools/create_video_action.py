"""Create a new conservative Action from normalized video motion data.

This is a first-pass video adapter: it uses silhouette motion for global/body
and tail motion, never copies an imported FBX Action.
"""
import argparse, json
from pathlib import Path
import bpy
from mathutils import Euler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--motion", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=args.model)
    rig = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
    mesh = next(o for o in bpy.context.scene.objects if o.type == "MESH")
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    data = json.loads(Path(args.motion).read_text(encoding="utf-8"))
    frames = data.get("frames", [])
    action = bpy.data.actions.new("CMAI_Balisk_From_MP4")
    action.use_fake_user = True
    rig.animation_data_create()
    rig.animation_data.action = action
    valid = [f for f in frames if f.get("landmarks")]
    if not valid:
        raise RuntimeError("Motion data contains no usable landmarks")
    first = valid[0]["landmarks"]
    base = first["motion_center"]
    for item in valid:
        lm = item["landmarks"]
        frame = int(item["frame"])
        cx, cy, _ = lm["motion_center"]
        top = lm["motion_top"][1]
        bottom = lm["motion_bottom"][1]
        span = max(bottom - top, 1e-5)
        root = rig.pose.bones.get("Root")
        body = rig.pose.bones.get("Body_02") or rig.pose.bones.get("Body_01")
        tail = rig.pose.bones.get("Tail_02")
        if root:
            root.location = ((cx - base[0]) * 0.8, 0.0, (base[1] - cy) * 0.8)
            root.keyframe_insert("location", frame=frame)
        if body:
            body.rotation_mode = "XYZ"
            body.rotation_euler = Euler(((base[1] - cy) * 0.45, (cx - base[0]) * 0.35, (span - 0.55) * 0.25), "XYZ")
            body.keyframe_insert("rotation_euler", frame=frame)
        if tail:
            tail.rotation_mode = "XYZ"
            tail.rotation_euler.z = (cx - base[0]) * 0.8
            tail.keyframe_insert("rotation_euler", frame=frame)
    scene = bpy.context.scene
    scene.frame_start = int(valid[0]["frame"])
    scene.frame_end = int(valid[-1]["frame"])
    rig["cmai_source_video"] = str(Path(args.motion).resolve())
    rig["cmai_new_action"] = action.name
    rig["cmai_existing_actions_used"] = False
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=args.output)
    print(json.dumps({"action": action.name, "frames": len(valid), "bones_keyed": ["Root", "Body_02", "Tail_02"], "output": args.output}))


if __name__ == "__main__":
    main()
