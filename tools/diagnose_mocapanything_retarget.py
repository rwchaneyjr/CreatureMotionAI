"""Read-only rig and motion diagnostics for the isolated MoCapAnything test."""
import bpy
import json
import math
import os
from mathutils import Matrix, Vector

bpy.ops.wm.open_mainfile(filepath=os.environ["CMAI_MOCAP_BLEND_IN"])
scene = bpy.context.scene
original = bpy.data.objects["CrimsonSpineBehemoth_Rig"]
source = bpy.data.objects["MoCapAnything_Balisk_24f_BVH"]
if os.environ.get("CMAI_MOCAP_APPLY_AXIS") == "1":
    source.matrix_world = Matrix(((0.0, -1.0, 0.0, 0.0),
                                  (0.0, 0.0, 1.0, 0.0),
                                  (-1.0, 0.0, 0.0, 0.0),
                                  (0.0, 0.0, 0.0, 1.0)))
rows = []
for name in sorted(original.data.bones.keys()):
    a, b = original.data.bones[name], source.data.bones[name]
    aw, bw = original.matrix_world @ a.matrix_local, source.matrix_world @ b.matrix_local
    rows.append({
        "bone": name,
        "original_parent": a.parent.name if a.parent else None,
        "source_parent": b.parent.name if b.parent else None,
        "head_error_world": (aw.translation-bw.translation).length,
        "tail_error_world": ((original.matrix_world @ a.tail_local)-(source.matrix_world @ b.tail_local)).length,
        "axis_error_degrees": math.degrees(aw.to_quaternion().rotation_difference(bw.to_quaternion()).angle),
        "original_length": a.length,
        "source_length": b.length,
        "original_rest_matrix": [list(r) for r in a.matrix_local],
        "source_rest_matrix": [list(r) for r in b.matrix_local],
    })
motion = {}
for frame in (1, 6, 12, 18, 24):
    scene.frame_set(frame)
    motion[str(frame)] = {n: {
        "head": list(source.matrix_world @ source.pose.bones[n].head),
        "tail": list(source.matrix_world @ source.pose.bones[n].tail),
        "basis_quaternion": list(source.pose.bones[n].matrix_basis.to_quaternion()),
        "basis_location": list(source.pose.bones[n].location),
    } for n in source.data.bones.keys()}
meshes = []
for obj in bpy.data.objects:
    if obj.type == "MESH":
        meshes.append({"name": obj.name, "vertices": len(obj.data.vertices),
                       "armature_modifiers": [m.object.name if m.object else None for m in obj.modifiers if m.type == "ARMATURE"],
                       "vertex_groups": len(obj.vertex_groups),
                       "materials": [m.name if m else None for m in obj.data.materials]})
report = {
    "source_blend": bpy.data.filepath,
    "original_matrix_world": [list(r) for r in original.matrix_world],
    "source_matrix_world": [list(r) for r in source.matrix_world],
    "original_action": original.animation_data.action.name if original.animation_data and original.animation_data.action else None,
    "source_action": source.animation_data.action.name if source.animation_data and source.animation_data.action else None,
    "scene_fps": scene.render.fps,
    "bone_comparison": rows,
    "sample_motion": motion,
    "meshes": meshes,
    "cameras": [o.name for o in bpy.data.objects if o.type == "CAMERA"],
}
out = os.environ["CMAI_MOCAP_DIAG_OUT"]
with open(out, "w", encoding="utf-8") as handle:
    json.dump(report, handle, indent=2)
print("CMAI_DIAGNOSTIC", out)
