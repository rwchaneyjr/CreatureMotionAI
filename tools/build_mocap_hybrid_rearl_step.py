"""Build one reference-guided Rear.L step with MoCapAnything axial motion.

This is an isolated proof of concept. It never changes the source rig file and
never keys any of the other seven leg chains. The 2D track is an unverified
observation, so the output report retains that distinction.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

from creature_motion_ai.ik_step import (
    restore_terminal_foot_world_orientation,
    solve_rest_relative_two_link,
    world_direction_pose_matrix,
)


def parse_args():
    parser = argparse.ArgumentParser()
    for name in ("original", "mocap", "track", "output", "report"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--body-weight", type=float, default=0.03)
    parser.add_argument("--head-tail-weight", type=float, default=0.30)
    parser.add_argument("--pixels-per-unit", type=float, default=500.0)
    parser.add_argument("--max-stride", type=float, default=0.16)
    parser.add_argument("--foot-down-pitch-degrees", type=float, default=0.0)
    parser.add_argument("--ground-via-reachable-ankle", action="store_true",
                        help="Bring the ankle toward the hip before lowering it to ground; preserve rest foot pitch")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    return parser.parse_args(argv)


def main():
    args = parse_args()
    if args.output.exists() or args.report.exists():
        raise RuntimeError("Refusing to overwrite an existing hybrid test")
    track = json.loads(args.track.read_text(encoding="utf-8"))
    rows = {int(row["frame"]): row for row in track["frames"]}
    if any(frame not in rows for frame in range(1, 33)):
        raise RuntimeError("Rear.L track must contain frames 1–32")

    bpy.ops.wm.open_mainfile(filepath=str(args.mocap.resolve()))
    mocap_arm = bpy.data.objects["CrimsonSpineBehemoth_Rig"]
    axial = [bone.name for bone in mocap_arm.data.bones if bone.name.startswith(("Body_", "Head_", "Tail_"))]
    mocap_quats = {}
    for frame in range(1, 25):
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        mocap_quats[frame] = {name: mocap_arm.pose.bones[name].matrix_basis.to_quaternion().copy()
                              for name in axial}

    bpy.ops.wm.open_mainfile(filepath=str(args.original.resolve()))
    scene = bpy.context.scene
    arm = bpy.data.objects["CrimsonSpineBehemoth_Rig"]
    mesh = next(obj for obj in scene.objects if obj.type == "MESH" and any(
        modifier.type == "ARMATURE" and modifier.object == arm for modifier in obj.modifiers))
    original_rest = {bone.name: bone.matrix_local.copy() for bone in arm.data.bones}
    original_actions = {action.name for action in bpy.data.actions}
    for action in bpy.data.actions:
        action.use_fake_user = True
    scene.frame_set(1)
    bpy.context.view_layer.update()
    chain = [f"Leg_Rear.L_{index:02}" for index in (1, 2, 3)]
    assert all(arm.pose.bones.get(name) and not arm.pose.bones[name].constraints for name in chain)
    rest_world = {name: arm.matrix_world @ arm.pose.bones[name].matrix.copy() for name in chain}
    hip0 = arm.matrix_world @ arm.pose.bones[chain[0]].head
    knee0 = arm.matrix_world @ arm.pose.bones[chain[0]].tail
    ankle0 = arm.matrix_world @ arm.pose.bones[chain[1]].tail
    tip0 = arm.matrix_world @ arm.pose.bones[chain[2]].tail
    foot_group = mesh.vertex_groups[chain[2]].index
    foot_indices = [vertex.index for vertex in mesh.data.vertices if any(
        weight.group == foot_group and weight.weight >= 0.25 for weight in vertex.groups)]
    if not foot_indices:
        raise RuntimeError("Rear.L has no terminal-foot skin weights")
    evaluated = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    baseline_mesh = evaluated.to_mesh()
    baseline_ground = min((evaluated.matrix_world @ vertex.co).z
                          for vertex in baseline_mesh.vertices)
    baseline_foot_floor = min((evaluated.matrix_world @ baseline_mesh.vertices[index].co).z
                              for index in foot_indices)
    evaluated.to_mesh_clear()
    rest_foot_gap = max(0.0, baseline_foot_floor - baseline_ground)
    upper_len = (knee0 - hip0).length
    lower_len = (ankle0 - knee0).length
    bend_normal = (knee0 - hip0).cross(ankle0 - hip0)
    safe_max = min(upper_len + lower_len - 0.0001,
                   max((upper_len + lower_len) * 0.985,
                       (ankle0 - hip0).length + 0.001))
    contact_forward = 0.0
    if args.ground_via_reachable_ankle:
        if args.foot_down_pitch_degrees:
            raise RuntimeError("Reachable-ankle contact preserves the original foot pitch")
        delta = ankle0 - hip0
        remaining_sq = safe_max**2 - delta.x**2 - (delta.z - rest_foot_gap)**2
        if remaining_sq <= 0 or delta.y <= 0:
            raise RuntimeError("Original Rear.L cannot reach ground by moving the ankle toward the hip along Y")
        contact_forward = max(0.0, delta.y - math.sqrt(remaining_sq)) + 0.002
    rest_basis = {name: arm.pose.bones[name].matrix_basis.to_quaternion().copy() for name in axial}
    base_uv = rows[1]["landmarks_2d"]
    base_relative_x = base_uv["foot"][0] - base_uv["hip"][0]
    base_relative_y = base_uv["foot"][1] - base_uv["hip"][1]

    action = bpy.data.actions.new("CMAI_Hybrid_MoCap_Body_Reference_RearL_Step")
    action.use_fake_user = True
    arm.animation_data_create()
    arm.animation_data.action = action
    scene.frame_start, scene.frame_end, scene.render.fps = 1, 32, 24
    identity = Quaternion((1.0, 0.0, 0.0, 0.0))
    report_rows = []
    previous_forward = 0.0

    for frame in range(1, 33):
        scene.frame_set(frame)
        # Official MoCap prediction covers only frames 1–24. The axial motion
        # is held at frame 24 during the landing; it is never extrapolated.
        source_frame = min(frame, 24)
        for name in axial:
            bone = arm.pose.bones[name]
            weight = args.body_weight if name.startswith("Body_") else args.head_tail_weight
            delta = mocap_quats[1][name].inverted() @ mocap_quats[source_frame][name]
            bone.rotation_mode = "QUATERNION"
            bone.rotation_quaternion = rest_basis[name] @ identity.slerp(delta, weight)
            bone.keyframe_insert(data_path="rotation_quaternion", frame=frame, group=name)
        bpy.context.view_layer.update()
        hip = arm.matrix_world @ arm.pose.bones[chain[0]].head

        row = rows[frame]
        uv, confidence = row["landmarks_2d"], row["confidence"]
        relative_x = uv["foot"][0] - uv["hip"][0]
        relative_y = uv["foot"][1] - uv["hip"][1]
        # The original rig faces -Y. From the +X camera, image-right is -Y.
        raw_forward = max(0.0, (relative_x - base_relative_x) / args.pixels_per_unit)
        forward = min(raw_forward, args.max_stride)
        # Contact until frame 12, then evidence-guided swing and landing.
        if frame <= 12:
            forward, lift = 0.0, 0.0
            phase = "contact"
        else:
            transition = min(1.0, max(0.0, (frame - 12) / 6.0))
            transition = transition * transition * (3.0 - 2.0 * transition)
            forward *= transition
            measured_lift = max(0.0, (base_relative_y - relative_y) / args.pixels_per_unit)
            # The tracker drifts from the toes to the ankle late in the swing.
            # Use its horizontal trajectory only after confidence falls, and
            # taper lift to zero when the video shows the new contact.
            if frame <= 20:
                lift = min(0.035, measured_lift) * transition
            else:
                landing = max(0.0, (32 - frame) / 12.0)
                lift = min(0.035, measured_lift) * landing
            phase = "swing" if frame < 31 else "landing"
        # The tracker jumps late in the swing. Bound per-frame target travel.
        forward = max(previous_forward - 0.015, min(previous_forward + 0.015, forward))
        previous_forward = forward
        # Keep the original foot-tip direction; solve to the ankle joint.
        # When the foot itself is pitched down to meet the ground, the ankle
        # must stay at its original rest height. Otherwise the short chain
        # would have to stretch beyond its actual two-link reach.
        ankle_drop = rest_foot_gap if (args.foot_down_pitch_degrees == 0 and
                                      args.ground_via_reachable_ankle) else 0.0
        desired_ankle = ankle0 + Vector((0.0, -forward - contact_forward,
                                        lift - ankle_drop)) + (hip - hip0)
        reach = desired_ankle - hip
        safe_min = abs(upper_len - lower_len) + 0.015
        reach_clamped = False
        if reach.length > safe_max or reach.length < safe_min:
            desired_ankle = hip + reach.normalized() * max(safe_min, min(safe_max, reach.length))
            reach_clamped = True
        solved = solve_rest_relative_two_link(
            hip, desired_ankle, upper_len, lower_len, bend_normal,
            min_knee_angle=math.radians(12.0))
        if solved["status"] != "PASS":
            raise RuntimeError(f"Rear.L solve failed at frame {frame}: {solved}")

        b1, b2, b3 = (arm.pose.bones[name] for name in chain)
        desired_upper = world_direction_pose_matrix(rest_world[chain[0]], hip0, hip,
                                                    solved["knee"], knee0)
        b1.matrix = arm.matrix_world.inverted() @ desired_upper
        bpy.context.view_layer.update()
        desired_lower = world_direction_pose_matrix(rest_world[chain[1]], knee0,
                                                    solved["knee"], desired_ankle, ankle0)
        b2.matrix = arm.matrix_world.inverted() @ desired_lower
        bpy.context.view_layer.update()
        restore_terminal_foot_world_orientation(
            arm, chain[2], rest_world[chain[2]], arm.matrix_world @ b2.tail)
        bpy.context.view_layer.update()
        if args.foot_down_pitch_degrees:
            foot_head = arm.matrix_world @ b3.head
            foot_world = arm.matrix_world @ b3.matrix.copy()
            pitch = Matrix.Rotation(math.radians(args.foot_down_pitch_degrees), 4, "Y")
            pitched_world = Matrix.Translation(foot_head) @ pitch @ Matrix.Translation(-foot_head) @ foot_world
            b3.matrix = arm.matrix_world.inverted() @ pitched_world
            bpy.context.view_layer.update()
        for bone in (b1, b2, b3):
            bone.rotation_mode = "QUATERNION"
            bone.keyframe_insert(data_path="rotation_quaternion", frame=frame, group=bone.name)
        tip = arm.matrix_world @ b3.tail
        knee = arm.matrix_world @ b1.tail
        bend = (knee - hip).cross(tip - hip)
        alignment = bend.normalized().dot(bend_normal.normalized()) if bend.length > 1e-8 else 0.0
        orientation = math.degrees((arm.matrix_world @ b3.matrix).to_quaternion().rotation_difference(
            rest_world[chain[2]].to_quaternion()).angle)
        report_rows.append({
            "frame": frame, "phase": phase, "mocap_source_frame": source_frame,
            "track_foot_confidence": confidence["foot"],
            "track_ankle_confidence": confidence["ankle"],
            "track_status": "UNVERIFIED_PREDICTION",
            "forward_offset": forward, "lift_offset": lift,
            "rest_contact_forward_offset": contact_forward,
            "reach_clamped": reach_clamped, "knee_bend_alignment": alignment,
            "foot_orientation_change_degrees": orientation,
            "hip": list(hip), "knee": list(knee),
            "ankle": list(arm.matrix_world @ b2.tail), "foot_tip": list(tip),
        })

    # A camera on +X exposes the original .L side; -X would show the far side.
    camera_data = bpy.data.cameras.new("CMAI_Hybrid_RearL_ReferenceSide")
    camera = bpy.data.objects.new(camera_data.name, camera_data)
    scene.collection.objects.link(camera)
    camera.location = Vector((3.0, -0.82, 0.11))
    camera.rotation_euler = (Vector((0.0, -0.82, 0.11)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = 2.0
    scene.camera = camera
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.color_type = "TEXTURE"
    scene.display.shading.background_type = "VIEWPORT"
    scene.display.shading.background_color = (0.93, 0.93, 0.93)
    scene.render.resolution_x, scene.render.resolution_y = 1280, 720
    scene.render.resolution_percentage = 100
    arm.show_in_front = False
    scene.frame_set(1)
    bpy.context.view_layer.update()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()))
    report = {
        "status": "BUILT_PENDING_VISUAL_AND_PHYSICAL_VALIDATION",
        "action": action.name, "frames": 32,
        "original_blend": str(args.original), "output_blend": str(args.output),
        "mocap_blend": str(args.mocap), "reference_track": str(args.track),
        "motion_sources": {"body_head_tail": "MoCapAnything prediction, frame-1-relative, weighted",
                           "Rear.L": "CreatureMotionAI 2D foot-relative-to-hip track, bounded two-link solve",
                           "other_seven_legs": "original standing pose"},
        "mocap_frame_25_32": "frame 24 held, no predicted frames invented",
        "body_weight": args.body_weight, "head_tail_weight": args.head_tail_weight,
        "projection": "approximately calibrated side-view pixels to armature Y/Z; no 3D triangulation",
        "original_rest_matrices_unchanged": all(arm.data.bones[name].matrix_local == matrix
                                                for name, matrix in original_rest.items()),
        "original_actions_preserved": original_actions.issubset({item.name for item in bpy.data.actions}),
        "all_knees_bend_original_direction": all(item["knee_bend_alignment"] > 0 for item in report_rows),
        "max_foot_orientation_change_degrees": max(item["foot_orientation_change_degrees"] for item in report_rows),
        "max_stride": max(item["forward_offset"] for item in report_rows),
        "max_lift": max(item["lift_offset"] for item in report_rows),
        "foot_down_pitch_degrees": args.foot_down_pitch_degrees,
        "ground_via_reachable_ankle": args.ground_via_reachable_ankle,
        "rest_contact_forward_offset": contact_forward,
        "original_weighted_foot_gap_above_ground": rest_foot_gap,
        "baseline_ground_z": baseline_ground,
        "frame_data": report_rows,
    }
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("CMAI_HYBRID_REARL", json.dumps({key: value for key, value in report.items() if key != "frame_data"}))


if __name__ == "__main__":
    main()
