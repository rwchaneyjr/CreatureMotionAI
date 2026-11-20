"""Combine the existing dragon FLAP cycle with a tucked four-leg pose.

Operates on a copied blend only. FLAP is sampled frame by frame; only the
four leg chains are replaced by a pose sampled from the existing RUN Action.
"""
import argparse
import json
import sys
from pathlib import Path

import bpy


LEG_BONES = [
    f"Leg_{region}.{side}_{segment}"
    for region in ("Front", "Rear")
    for side in ("L", "R")
    for segment in ("01", "02", "03")
]


def arguments():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--report", required=True)
    p.add_argument("--flap-action", default="FLAP")
    p.add_argument("--tuck-action", default="RUN")
    p.add_argument("--tuck-frame", type=int, default=30)
    p.add_argument("--frames", type=int, default=120)
    return p.parse_args(argv)


def assign(rig, action):
    rig.animation_data_create()
    rig.animation_data.action = action
    if hasattr(rig.animation_data, "action_slot") and action.slots:
        rig.animation_data.action_slot = action.slots[0]


def capture(rig, action, frame):
    assign(rig, action)
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    return {
        "location": rig.location.copy(),
        "rotation": (rig.rotation_quaternion.copy() if rig.rotation_mode == "QUATERNION"
                     else rig.rotation_euler.to_quaternion()),
        "scale": rig.scale.copy(),
        "bones": {pb.name: pb.matrix_basis.copy().decompose() for pb in rig.pose.bones},
    }


def put_pose(rig, pose):
    rig.location = pose["location"]
    rig.rotation_mode = "QUATERNION"
    rig.rotation_quaternion = pose["rotation"]
    rig.scale = pose["scale"]
    for pb in rig.pose.bones:
        loc, rot, scale = pose["bones"][pb.name]
        pb.location = loc
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = rot
        pb.scale = scale


def main():
    a = arguments()
    source, output, report_path = map(lambda x: Path(x).resolve(), (a.source, a.output, a.report))
    output.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(source))
    rig = bpy.data.objects.get("CrimsonWingedDragon_Rig")
    if not rig or rig.type != "ARMATURE" or len(rig.data.bones) != 47:
        raise RuntimeError("Expected the copied original 47-bone dragon armature")
    if any(name not in rig.data.bones for name in LEG_BONES):
        raise RuntimeError("One or more expected four-leg chains are absent")
    if bpy.data.actions.get("Fly Feet Tuck"):
        raise RuntimeError("Refusing to overwrite existing Action 'Fly Feet Tuck'")
    flap = bpy.data.actions.get(a.flap_action)
    tuck_source = bpy.data.actions.get(a.tuck_action)
    if flap is None or tuck_source is None:
        raise RuntimeError("Required source Actions FLAP/RUN were not found")
    if not int(tuck_source.frame_range[0]) <= a.tuck_frame <= int(tuck_source.frame_range[1]):
        raise RuntimeError("Tuck source frame is outside its Action range")
    if a.frames > int(flap.frame_range[1] - flap.frame_range[0] + 1):
        raise RuntimeError("Requested duration exceeds sampled FLAP Action range")

    tuck_pose = capture(rig, tuck_source, a.tuck_frame)
    new_action = bpy.data.actions.new("Fly Feet Tuck")
    new_action.use_fake_user = True
    new_action.slots.new(id_type="OBJECT", name=rig.name)
    assign(rig, new_action)
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"

    flap_start = int(flap.frame_range[0])
    for i in range(a.frames):
        source_frame = flap_start + i
        flap_pose = capture(rig, flap, source_frame)
        # Restore the sampled flap pose, then keep leg chains in the tucked pose.
        assign(rig, new_action)
        put_pose(rig, flap_pose)
        for name in LEG_BONES:
            pb = rig.pose.bones[name]
            loc, rot, scale = tuck_pose["bones"][name]
            pb.location = loc
            pb.rotation_quaternion = rot
            pb.scale = scale
        key = i + 1
        for pb in rig.pose.bones:
            pb.keyframe_insert("location", frame=key, group=pb.name)
            pb.keyframe_insert("rotation_quaternion", frame=key, group=pb.name)
            pb.keyframe_insert("scale", frame=key, group=pb.name)
        rig.keyframe_insert("location", frame=key, group="Armature Object")
        rig.keyframe_insert("rotation_quaternion", frame=key, group="Armature Object")
        rig.keyframe_insert("scale", frame=key, group="Armature Object")

    # Dense samples plus linear interpolation follow the source wing curves
    # without Bézier overshoot, and preserve exact sampled cycle boundaries.
    for layer in new_action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:
                        key.interpolation = "LINEAR"
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end, scene.render.fps = 1, a.frames, 24
    assign(rig, new_action)
    scene.frame_set(1)
    bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(output))
    report = {
        "status": "ACTION_CREATED_VISUAL_REVIEW_REQUIRED",
        "source_blend_copy": str(source), "output_blend": str(output),
        "action": new_action.name, "rig": rig.name, "bone_count": len(rig.data.bones),
        "duration_frames": a.frames, "fps": 24, "duration_seconds": a.frames / 24,
        "wings_and_body": f"Sampled from {a.flap_action} frame {flap_start} onward, retaining its original wing-flap timing.",
        "leg_pose": f"All four existing 3-bone leg chains held in the tucked pose sampled from {a.tuck_action} frame {a.tuck_frame}; this is a pose-based approximation, not per-frame mocap retargeting.",
        "leg_bones": LEG_BONES,
        "original_actions_preserved": True,
        "rest_data_mesh_weights_hierarchy_modified": False,
        "reference_video": r"C:\Users\rober\Desktop\dragon fly feet tucked !~.mp4",
        "reference_limit": "Single side view; hidden far-side joint trajectories are not reconstructed.",
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
