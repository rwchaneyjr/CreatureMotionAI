"""Read-only geometry inspection for the MoCapAnything/Rear.L hybrid test."""
import bpy
import json
import os
from pathlib import Path

from mathutils import Vector


def xyz(vector):
    return [round(float(value), 6) for value in vector]


bpy.ops.wm.open_mainfile(filepath=os.environ["CMAI_HYBRID_ORIGINAL"])
scene = bpy.context.scene
scene.frame_set(1)
bpy.context.view_layer.update()
arm = bpy.data.objects["CrimsonSpineBehemoth_Rig"]
mesh = next(obj for obj in scene.objects if obj.type == "MESH" and any(
    modifier.type == "ARMATURE" and modifier.object == arm for modifier in obj.modifiers))
legs = {}
for prefix in ("Leg_Rear.L", "Leg_Rear.R", "Leg_MidRear.L", "Leg_MidRear.R"):
    chain = [arm.pose.bones[f"{prefix}_{part:02}"] for part in (1, 2, 3)]
    legs[prefix] = {"head": [xyz(arm.matrix_world @ bone.head) for bone in chain],
                    "tail": [xyz(arm.matrix_world @ bone.tail) for bone in chain]}
data = {"rig_bones": len(arm.data.bones), "mesh_vertices": len(mesh.data.vertices),
        "armature_matrix": [[float(v) for v in row] for row in arm.matrix_world],
        "legs": legs, "camera": scene.camera.name if scene.camera else None,
        "axial_bones": {name: {"head": xyz(arm.matrix_world @ arm.pose.bones[name].head),
                                "tail": xyz(arm.matrix_world @ arm.pose.bones[name].tail)}
                         for name in ("Head_01", "Head_02", "Body_01", "Tail_01", "Tail_08")},
        "actions": [action.name for action in bpy.data.actions]}
Path(os.environ["CMAI_HYBRID_INSPECT_OUT"]).write_text(json.dumps(data, indent=2), encoding="utf-8")
print("CMAI_HYBRID_INSPECT", json.dumps(data))
