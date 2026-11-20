"""Bake a small posterior yaw onto both rear leg chains in a copy of a walk.

The source .blend is opened read-only and is never saved in place.  Existing
animation is sampled frame-by-frame, the two rear chains are yawed around their
own hip joints, and a new Action is baked to a new .blend file.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--angle-deg", type=float, default=5.0)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=41)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])

    source = Path(args.blend).resolve()
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(source))
    scene = bpy.context.scene
    arm = next(obj for obj in scene.objects if obj.type == "ARMATURE")
    old_action = arm.animation_data.action if arm.animation_data else None
    if not old_action:
        raise RuntimeError("Input armature has no active Action")
    old_name = old_action.name
    angle = math.radians(args.angle_deg)
    up = Vector((0.0, 0.0, 1.0))
    world_delta = Matrix.Rotation(angle, 4, up)
    arm_inv = arm.matrix_world.inverted()

    # A layered Action and slot are required by Blender 5.x.
    action = bpy.data.actions.new("CMAI_RearClearance_" + out.stem)
    action.use_fake_user = True
    slot = action.slots.new(id_type='OBJECT', name=arm.name)
    arm.animation_data_create()
    arm.animation_data.action = action
    arm.animation_data.action_slot = slot
    for pose_bone in arm.pose.bones:
        pose_bone.rotation_mode = "QUATERNION"

    rows = []
    for frame in range(args.start, args.end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        for side in ("L", "R"):
            hip = arm.pose.bones[f"Leg_Rear.{side}_01"]
            hip_world = arm.matrix_world @ hip.head
            pivot = Matrix.Translation(hip_world)
            unpivot = Matrix.Translation(-hip_world)
            current_world = arm.matrix_world @ hip.matrix
            hip.matrix = arm_inv @ pivot @ world_delta @ unpivot @ current_world
            bpy.context.view_layer.update()

        # Bake the complete evaluated rig pose so the new Action is self
        # contained and does not depend on the original Action at playback.
        for pose_bone in arm.pose.bones:
            pose_bone.keyframe_insert("location", frame=frame, group=pose_bone.name)
            pose_bone.keyframe_insert("rotation_quaternion", frame=frame, group=pose_bone.name)
            pose_bone.keyframe_insert("scale", frame=frame, group=pose_bone.name)
        rows.append({"frame": frame,
                     "rear_hip_world": {side: list(arm.matrix_world @ arm.pose.bones[f"Leg_Rear.{side}_01"].head)
                                        for side in ("L", "R")}})

    # Keep quaternion interpolation safe and loop the 40-frame gait.
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:
                        if "rotation_quaternion" in curve.data_path:
                            key.interpolation = "LINEAR"
                        else:
                            key.interpolation = "BEZIER"
                            key.handle_left_type = "AUTO_CLAMPED"
                            key.handle_right_type = "AUTO_CLAMPED"
                    if len(curve.keyframe_points) > 1:
                        curve.modifiers.new("CYCLES")

    scene.frame_start = args.start
    scene.frame_end = 120
    scene.frame_set(args.start)
    bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(out))
    report = {
        "status": "CANDIDATE_BAKED",
        "source_blend": str(source),
        "candidate_blend": str(out),
        "source_action": old_name,
        "new_action": action.name,
        "rear_leg_yaw_degrees": args.angle_deg,
        "rotation_axis_world": list(up),
        "direction": "posterior around each hip; source forward axis is (0,-1,0)",
        "frames_baked": [args.start, args.end],
        "rig_bone_count": len(arm.data.bones),
        "original_rest_data_changed": False,
        "frames": rows,
        "validation": "PENDING_EVALUATED_MESH_COLLISION_AND_CONTACT_CHECKS"
    }
    out.with_suffix(".candidate.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "blend": str(out), "action": action.name,
                      "angle_deg": args.angle_deg}))


if __name__ == "__main__":
    main()
