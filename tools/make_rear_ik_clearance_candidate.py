"""Add a small rest-length-preserving posterior foot shift to a copied walk."""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from creature_motion_ai import ik_step


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blend", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--offset", type=float, default=0.01)
    ap.add_argument("--mode", choices=("foot_ik", "whole_chain"), default="foot_ik")
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--end", type=int, default=41)
    args = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
    source, out = Path(args.blend).resolve(), Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(source))
    scene = bpy.context.scene
    arm = next(o for o in scene.objects if o.type == "ARMATURE")
    mesh = next(o for o in scene.objects if o.type == "MESH")
    old_action = arm.animation_data.action if arm.animation_data else None
    if old_action is None:
        raise RuntimeError("Input has no active walk Action")
    old_action_name = old_action.name
    ordered = sorted(arm.pose.bones, key=lambda p: len(p.parent_recursive))
    inv_arm = arm.matrix_world.inverted()

    # Cache the existing animated world pose before creating a new Action.
    baseline = {}
    for frame in range(args.start, args.end + 1):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        baseline[frame] = {p.name: (arm.matrix_world @ p.matrix).copy() for p in ordered}

    # Cache neutral bend/length evidence from the actual start of each frame.
    action = bpy.data.actions.new("CMAI_RearIKClearance_" + out.stem)
    action.use_fake_user = True
    slot = action.slots.new(id_type='OBJECT', name=arm.name)
    arm.animation_data.action = action
    arm.animation_data.action_slot = slot
    for p in ordered:
        p.rotation_mode = "QUATERNION"

    posterior_world = (arm.matrix_world.to_3x3() @ Vector((0.0, 1.0, 0.0))).normalized()
    rows = []
    for frame in range(args.start, args.end + 1):
        scene.frame_set(frame)
        # Restore the exact saved source pose, parent-first, before fitting.
        for p in ordered:
            p.matrix = inv_arm @ baseline[frame][p.name]
            bpy.context.view_layer.update()

        leg_rows = {}
        for side in ("L", "R"):
            names = [f"Leg_Rear.{side}_{i:02d}" for i in (1, 2, 3)]
            bones = [arm.pose.bones[n] for n in names]
            points = [arm.matrix_world @ bones[0].head,
                      arm.matrix_world @ bones[0].tail,
                      arm.matrix_world @ bones[1].tail,
                      arm.matrix_world @ bones[2].tail]
            matrices = [arm.matrix_world @ p.matrix for p in bones]
            lengths = [(points[i + 1] - points[i]).length for i in range(3)]
            normal = (points[1] - points[0]).cross(points[2] - points[0])
            if normal.length < 1e-8:
                raise RuntimeError(f"Degenerate original knee plane: Rear.{side}, frame {frame}")
            normal.normalize()
            if args.mode == "whole_chain":
                # Move only the upper pose root. Descendants follow through
                # the original hierarchy, leaving all joint rotations intact.
                world_shift = posterior_world * args.offset
                local_shift = inv_arm.to_3x3() @ world_shift
                shifted = bones[0].matrix.copy()
                shifted.translation += local_shift
                bones[0].matrix = shifted
                bpy.context.view_layer.update()
                solution = {"status": "PASS", "knee": arm.matrix_world @ bones[1].head}
            else:
                target = points[2] + posterior_world * args.offset
                solution = ik_step.solve_rest_relative_two_link(points[0], target, lengths[0], lengths[1], normal,
                                                                 min_knee_angle=math.radians(8))
                if solution.get("status") != "PASS":
                    raise RuntimeError(f"IK rejected Rear.{side} frame {frame}: {solution}")
                knee = solution["knee"]
                for i, (head, tail) in enumerate(((points[0], knee), (knee, target))):
                    pose_matrix = ik_step.world_direction_pose_matrix(matrices[i], points[i], head, tail, points[i + 1])
                    bones[i].matrix = inv_arm @ pose_matrix
                    bpy.context.view_layer.update()
                ik_step.restore_terminal_foot_world_orientation(arm, names[2], matrices[2], target)
                bpy.context.view_layer.update()
            actual = [arm.matrix_world @ arm.pose.bones[n].head for n in names]
            actual.append(arm.matrix_world @ arm.pose.bones[names[-1]].tail)
            length_errors = [abs((actual[i + 1] - actual[i]).length - lengths[i]) for i in range(3)]
            actual_normal = (actual[1] - actual[0]).cross(actual[2] - actual[0]).normalized()
            actual_knee_angle = (actual[0] - actual[1]).angle(actual[2] - actual[1])
            foot_angle = (arm.matrix_world @ arm.pose.bones[names[2]].matrix).to_quaternion().rotation_difference(
                matrices[2].to_quaternion()).angle
            leg_rows[side] = {
                "status": "PASS" if max(length_errors) < 1e-4 and actual_normal.dot(normal) > 0.99 else "FAIL",
                "target_shift_world": list(posterior_world * args.offset),
                "actual_foot_shift_world": list(actual[-1] - points[-1]),
                "max_bone_length_error": max(length_errors),
                "knee_flexion_deg": 180.0 - math.degrees(actual_knee_angle),
                "knee_bend_dot_vs_original": actual_normal.dot(normal),
                "foot_orientation_change_deg": math.degrees(foot_angle),
            }
            if leg_rows[side]["status"] != "PASS":
                raise RuntimeError(f"Anatomical validation failed: Rear.{side}, frame {frame}: {leg_rows[side]}")

        # Key the complete local pose into a new standalone Action.
        for p in ordered:
            p.keyframe_insert("location", frame=frame, group=p.name)
            p.keyframe_insert("rotation_quaternion", frame=frame, group=p.name)
            p.keyframe_insert("scale", frame=frame, group=p.name)
        rows.append({"frame": frame, "legs": leg_rows})

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
        "status": "IK_CANDIDATE_BAKED",
        "source_blend": str(source),
        "candidate_blend": str(out),
        "source_action": old_action_name,
        "new_action": action.name,
        "posterior_offset_blender_units": args.offset,
        "posterior_direction_world": list(posterior_world),
        "method": ("whole rear chain translated posterior with original joint rotations retained" if args.mode == "whole_chain" else "rest-length-preserving two-link IK using each frame's original hip, knee plane, ankle and foot orientation"),
        "mode": args.mode,
        "frames_baked": [args.start, args.end],
        "frames": rows,
        "mesh_collision_validation": "PENDING",
        "contact_and_slip_validation": "PENDING",
    }
    out.with_suffix(".candidate.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "blend": str(out), "offset": args.offset}))


if __name__ == "__main__":
    main()
