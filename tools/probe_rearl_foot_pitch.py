"""Measure whether bounded original-foot pitch can reach model ground."""
import json
import os
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


source = Path(os.environ["CMAI_HYBRID_ORIGINAL"])
report_path = Path(os.environ["CMAI_HYBRID_PITCH_REPORT"])
bpy.ops.wm.open_mainfile(filepath=str(source.resolve()))
scene = bpy.context.scene
scene.frame_set(1)
arm = bpy.data.objects["CrimsonSpineBehemoth_Rig"]
mesh = next(obj for obj in scene.objects if obj.type == "MESH" and any(
    mod.type == "ARMATURE" and mod.object == arm for mod in obj.modifiers))
group = mesh.vertex_groups["Leg_Rear.L_03"].index
indices = [vertex.index for vertex in mesh.data.vertices if any(
    item.group == group and item.weight >= 0.25 for item in vertex.groups)]
bone = arm.pose.bones["Leg_Rear.L_03"]
rest_world = arm.matrix_world @ bone.matrix.copy()
head = arm.matrix_world @ bone.head


def sample():
    evaluated = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    temporary = evaluated.to_mesh()
    ground = min((evaluated.matrix_world @ vertex.co).z for vertex in temporary.vertices)
    foot = min((evaluated.matrix_world @ temporary.vertices[index].co).z for index in indices)
    evaluated.to_mesh_clear()
    return ground, foot


original_ground, original_foot = sample()
rows = []
for degrees in (-25, -20, -15, -10, -5, 0, 5, 10, 15, 20, 25):
    rotation = Matrix.Rotation(__import__("math").radians(degrees), 4, "Y")
    new_world = Matrix.Translation(head) @ rotation @ Matrix.Translation(-head) @ rest_world
    bone.matrix = arm.matrix_world.inverted() @ new_world
    bpy.context.view_layer.update()
    _, foot = sample()
    rows.append({"pitch_degrees": degrees, "foot_gap_to_original_ground": foot - original_ground})
report = {"original_ground_z": original_ground, "original_foot_z": original_foot,
          "original_gap": original_foot - original_ground, "pitch_test": rows,
          "source_changed": False}
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report))
