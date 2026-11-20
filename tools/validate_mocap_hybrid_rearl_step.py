"""Physically inspect and render the isolated 32-frame Rear.L hybrid test."""
import json
import math
import os
from pathlib import Path

import bpy
from mathutils import Vector


source = Path(os.environ["CMAI_HYBRID_BLEND"])
render_dir = Path(os.environ["CMAI_HYBRID_RENDER_DIR"])
report_path = Path(os.environ["CMAI_HYBRID_VALIDATION"])
render_dir.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(source.resolve()))
scene = bpy.context.scene
arm = bpy.data.objects["CrimsonSpineBehemoth_Rig"]
mesh = next(obj for obj in scene.objects if obj.type == "MESH" and any(
    mod.type == "ARMATURE" and mod.object == arm for mod in obj.modifiers))
chain = [f"Leg_Rear.L_{index:02}" for index in (1, 2, 3)]
foot_group = mesh.vertex_groups[chain[2]].index
foot_indices = [vertex.index for vertex in mesh.data.vertices if any(
    weight.group == foot_group and weight.weight >= 0.25 for weight in vertex.groups)]
if not foot_indices:
    raise RuntimeError("No weighted Rear.L terminal-foot vertices")
scene.frame_set(1)
bpy.context.view_layer.update()


def sample_vertices():
    evaluated = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    temporary = evaluated.to_mesh()
    world = evaluated.matrix_world
    sampled = [world @ temporary.vertices[index].co for index in foot_indices]
    minimum = min((world @ vertex.co).z for vertex in temporary.vertices)
    evaluated.to_mesh_clear()
    return sampled, minimum


baseline_foot, original_ground = sample_vertices()
bone_lengths = {name: arm.data.bones[name].length for name in chain}
rest_matrices = {bone.name: bone.matrix_local.copy() for bone in arm.data.bones}
rest_foot_orientation = (arm.matrix_world @ arm.pose.bones[chain[2]].matrix).to_quaternion()
rest_hip = arm.matrix_world @ arm.pose.bones[chain[0]].head
rest_knee = arm.matrix_world @ arm.pose.bones[chain[0]].tail
rest_ankle = arm.matrix_world @ arm.pose.bones[chain[1]].tail
rest_normal = (rest_knee - rest_hip).cross(rest_ankle - rest_hip).normalized()
other_leg_names = [bone.name for bone in arm.data.bones if bone.name.startswith("Leg_")
                   and not bone.name.startswith("Leg_Rear.L_")]
other_leg_basis = {name: arm.pose.bones[name].matrix_basis.copy() for name in other_leg_names}
max_other_leg_local_change = 0.0
scene.render.image_settings.file_format = "PNG"
frames = []
for frame in range(1, 33):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    foot_vertices, mesh_min_z = sample_vertices()
    foot_min_z = min(point.z for point in foot_vertices)
    hip = arm.matrix_world @ arm.pose.bones[chain[0]].head
    knee = arm.matrix_world @ arm.pose.bones[chain[0]].tail
    ankle = arm.matrix_world @ arm.pose.bones[chain[1]].tail
    tip = arm.matrix_world @ arm.pose.bones[chain[2]].tail
    bend = (knee - hip).cross(ankle - hip)
    bend_dot = bend.normalized().dot(rest_normal) if bend.length > 1e-8 else 0.0
    foot_orientation = (arm.matrix_world @ arm.pose.bones[chain[2]].matrix).to_quaternion()
    max_other_leg_local_change = max(max_other_leg_local_change, *(
        math.degrees((arm.pose.bones[name].matrix_basis.to_quaternion().rotation_difference(
            other_leg_basis[name].to_quaternion())).angle) for name in other_leg_names))
    rows = {
        "frame": frame, "foot_min_z": foot_min_z,
        "foot_clearance_vs_rest": foot_min_z - min(point.z for point in baseline_foot),
        "foot_clearance_above_ground": foot_min_z - original_ground,
        "foot_penetration": max(0.0, original_ground - foot_min_z),
        "whole_mesh_penetration": max(0.0, original_ground - mesh_min_z),
        "foot_y": tip.y, "foot_tip_z": tip.z,
        "foot_orientation_degrees": math.degrees(foot_orientation.rotation_difference(
            rest_foot_orientation).angle),
        "knee_bend_alignment": bend_dot,
        "upper_bone_length_error": abs((knee - hip).length - bone_lengths[chain[0]]),
        "lower_bone_length_error": abs((ankle - knee).length - bone_lengths[chain[1]]),
    }
    frames.append(rows)
    if frame in (1, 12, 18, 24, 30, 32):
        scene.render.filepath = str(render_dir / f"frame_{frame:02}.png")
        bpy.ops.render.render(write_still=True)

ground_pens = [item["whole_mesh_penetration"] for item in frames]
report = {
    "status": "REARL_LOCAL_CHECK_PASS_GLOBAL_VISUAL_REVIEW_REQUIRED" if (
        max(ground_pens) < 0.01 and all(item["knee_bend_alignment"] > 0 for item in frames)
        and max(item["foot_orientation_degrees"] for item in frames) < 5.0
        and max(item["foot_clearance_vs_rest"] for item in frames) > 0.01
    ) else "PHYSICAL_FAIL",
    "source_blend": str(source), "frame_count": 32,
    "weighted_rearL_foot_vertices": len(foot_indices),
    "original_ground_z": original_ground,
    "max_whole_mesh_ground_penetration": max(ground_pens),
    "max_rearL_foot_ground_penetration": max(item["foot_penetration"] for item in frames),
    "max_rearL_foot_clearance": max(item["foot_clearance_above_ground"] for item in frames),
    "max_rearL_foot_orientation_change_degrees": max(item["foot_orientation_degrees"] for item in frames),
    "minimum_knee_bend_alignment": min(item["knee_bend_alignment"] for item in frames),
    "rest_matrices_unchanged": all(arm.data.bones[name].matrix_local == matrix
                                   for name, matrix in rest_matrices.items()),
    "source_mesh_vertex_count": len(mesh.data.vertices),
    "rearL_tip_y_displacement": frames[-1]["foot_y"] - frames[0]["foot_y"],
    "other_seven_leg_max_local_rotation_change_degrees": max_other_leg_local_change,
    "other_seven_leg_channels_unchanged": max_other_leg_local_change < 0.001,
    "self_collision": "UNTESTED",
    "scope_note": "Rear.L local kinematics only. This does not validate whole-creature posture, other-leg support, or visual similarity.",
    "frames": frames,
}
report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
print("CMAI_HYBRID_VALIDATE", json.dumps({key: value for key, value in report.items() if key != "frames"}))
