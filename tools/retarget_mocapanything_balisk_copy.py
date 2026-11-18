"""Transfer isolated MoCapAnything BVH joint motion to a COPY of the original rig.

Requires the BVH to have been imported with global_scale=100. Never edits the source file.
The source and target bone heads must align after the explicit BVH-to-Blender axis map.
"""
import bpy
import json
import math
import os
from pathlib import Path
from mathutils import Matrix, Vector

inp = Path(os.environ["CMAI_MOCAP_BLEND_IN"])
out = Path(os.environ["CMAI_MOCAP_RETARGET_OUT"])
report_path = Path(os.environ["CMAI_MOCAP_RETARGET_REPORT"])
render_dir = Path(os.environ["CMAI_MOCAP_RENDER_DIR"])
if out.exists():
    raise RuntimeError(f"Refusing to overwrite prior test: {out}")
bpy.ops.wm.open_mainfile(filepath=str(inp))
scene = bpy.context.scene
target = bpy.data.objects["CrimsonSpineBehemoth_Rig"]
source = bpy.data.objects["MoCapAnything_Balisk_24f_BVH"]
mesh = next(o for o in bpy.data.objects if o.type == "MESH" and any(
    m.type == "ARMATURE" and m.object == target for m in o.modifiers))
original_actions = sorted(a.name for a in bpy.data.actions)
original_rest = {b.name: [list(row) for row in b.matrix_local] for b in target.data.bones}
source.matrix_world = Matrix(((0.0, -1.0, 0.0, 0.0),
                              (0.0, 0.0, 1.0, 0.0),
                              (-1.0, 0.0, 0.0, 0.0),
                              (0.0, 0.0, 0.0, 1.0)))
names = {b.name for b in target.data.bones}
if names != {b.name for b in source.data.bones} or len(names) != 38:
    raise RuntimeError("Original and BVH skeleton names differ")
rest_errors = []
for n in sorted(names):
    a, b = target.data.bones[n], source.data.bones[n]
    if (a.parent.name if a.parent else None) != (b.parent.name if b.parent else None):
        raise RuntimeError(f"Hierarchy mismatch at {n}")
    err = ((target.matrix_world @ a.head_local) - (source.matrix_world @ b.head_local)).length
    rest_errors.append(err)
if max(rest_errors) > 0.001:
    raise RuntimeError(f"BVH joint centers differ from original rest pose: {max(rest_errors):.6f}")

leg_names = sorted({n.rsplit("_", 1)[0] for n in names if n.startswith("Leg_") and n.endswith("_01")})
if len(leg_names) != 8:
    raise RuntimeError(f"Expected 8 leg chains, found {len(leg_names)}")
for pb in target.pose.bones:
    if pb.constraints:
        raise RuntimeError(f"Target bone has constraints that could conflict with transfer: {pb.name}")
target.animation_data_clear()
action = bpy.data.actions.new("CMAI_MoCapAnything_Balisk_24f_RestPreserving")
target.animation_data_create()
target.animation_data.action = action
ordered = sorted(names, key=lambda n: len(list(source.data.bones[n].parent_recursive)))
scene.frame_start, scene.frame_end = 1, 24
scene.render.fps = 24
zero_first_frame = os.environ.get("CMAI_MOCAP_ZERO_FIRST_FRAME") == "1"
scene.frame_set(1)
bpy.context.view_layer.update()
source_first = {n: source.matrix_world @ source.pose.bones[n].matrix.copy() for n in ordered}

# Ground and deformation baseline are measured on the unchanged skinned source mesh.
scene.frame_set(1)
deps = bpy.context.evaluated_depsgraph_get()
evaluated = mesh.evaluated_get(deps)
baseline_mesh = evaluated.to_mesh()
ground = min((mesh.matrix_world @ v.co).z for v in baseline_mesh.vertices)
baseline_vertices = {i: mesh.matrix_world @ baseline_mesh.vertices[i].co.copy()
                     for i in range(0, len(baseline_mesh.vertices), 997)}
evaluated.to_mesh_clear()
rest_foot = {}
for leg in leg_names:
    chain = [f"{leg}_{k:02d}" for k in (1, 2, 3)]
    rest_foot[leg] = {
        "hip": target.matrix_world @ target.data.bones[chain[0]].head_local,
        "knee": target.matrix_world @ target.data.bones[chain[1]].head_local,
        "ankle": target.matrix_world @ target.data.bones[chain[2]].head_local,
        "tip": target.matrix_world @ target.data.bones[chain[2]].tail_local,
    }

rows = []
for frame in range(1, 25):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    desired = {}
    for n in ordered:
        sr = source.matrix_world @ source.data.bones[n].matrix_local
        sp = source.matrix_world @ source.pose.bones[n].matrix
        tr = target.matrix_world @ target.data.bones[n].matrix_local
        baseline = source_first[n] if zero_first_frame else sr
        desired[n] = target.matrix_world.inverted() @ (sp @ baseline.inverted() @ tr)
    for n in ordered:
        pb = target.pose.bones[n]
        pb.rotation_mode = "QUATERNION"
        pb.matrix = desired[n]
        bpy.context.view_layer.update()
    for n in ordered:
        pb = target.pose.bones[n]
        pb.keyframe_insert(data_path="rotation_quaternion", frame=frame, group=n)
        if n == "Root":
            pb.keyframe_insert(data_path="location", frame=frame, group=n)
    bpy.context.view_layer.update()
    legs = {}
    for leg in leg_names:
        chain = [f"{leg}_{k:02d}" for k in (1, 2, 3)]
        hp = target.matrix_world @ target.pose.bones[chain[0]].head
        kp = target.matrix_world @ target.pose.bones[chain[1]].head
        ap = target.matrix_world @ target.pose.bones[chain[2]].head
        tp = target.matrix_world @ target.pose.bones[chain[2]].tail
        rest = rest_foot[leg]
        foot_angle = math.degrees((tp-ap).angle(rest["tip"]-rest["ankle"]))
        legs[leg] = {"hip": list(hp), "knee": list(kp), "ankle": list(ap), "tip": list(tp),
                     "foot_height_over_rest_ground": tp.z-ground,
                     "foot_orientation_change_degrees": foot_angle,
                     "tip_displacement_from_rest": (tp-rest["tip"]).length}
    row = {"frame": frame, "legs": legs}
    if frame in (1, 6, 12, 18, 24):
        ev = mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
        temp = ev.to_mesh()
        row["mesh_ground_penetration"] = max(0.0, ground-min((mesh.matrix_world @ v.co).z for v in temp.vertices))
        row["sampled_mesh_vertex_max_displacement"] = max(
            (mesh.matrix_world @ temp.vertices[i].co - base).length for i, base in baseline_vertices.items())
        ev.to_mesh_clear()
    rows.append(row)

source.hide_render = True
source.hide_viewport = True
source.hide_set(True)
target.show_in_front = False
target.hide_render = False
mesh.hide_render = False
mesh.hide_viewport = False

# Create a fixed side camera for a direct visual comparison. The rig and mesh stay unchanged.
cam_data = bpy.data.cameras.new("CMAI_MoCap_POC_Side_Camera")
cam = bpy.data.objects.new(cam_data.name, cam_data)
scene.collection.objects.link(cam)
cam.location = Vector((-3.0, 0.0, 0.18))
cam.rotation_euler = (Vector((0.0, -0.20, 0.18))-cam.location).to_track_quat("-Z", "Y").to_euler()
cam_data.type = "ORTHO"
cam_data.ortho_scale = 2.6
scene.camera = cam
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "TEXTURE"
scene.display.shading.show_cavity = True
scene.display.shading.background_type = "VIEWPORT"
scene.display.shading.background_color = (0.92, 0.92, 0.92)
scene.render.resolution_x = 640
scene.render.resolution_y = 360
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
render_dir.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out))
for frame in range(1, 25):
    scene.frame_set(frame)
    scene.render.filepath = str(render_dir / f"frame_{frame:04d}.png")
    bpy.ops.render.render(write_still=True)

rest_unchanged = all([list(row) for row in target.data.bones[n].matrix_local] == matrix
                     for n, matrix in original_rest.items())
report = {
    "source": str(inp), "output_blend": str(out), "action": action.name,
    "source_bvh_action": source.animation_data.action.name if source.animation_data and source.animation_data.action else None,
    "original_actions_preserved": all(n in bpy.data.actions for n in original_actions),
    "original_bone_rest_matrices_unchanged": rest_unchanged,
    "mesh_vertices": len(mesh.data.vertices),
    "mesh_armature_modifier": [m.object.name for m in mesh.modifiers if m.type == "ARMATURE"],
    "max_rest_joint_center_error": max(rest_errors), "original_ground_z": ground,
    "frame_rate_note": "BVH encoded at 30 FPS; 24 frame samples are displayed at 24 FPS for the 24 FPS reference clip.",
    "first_frame_as_rest_baseline": zero_first_frame,
    "frames": rows,
    "render_dir": str(render_dir),
    "status": "TRANSFERRED_FOR_VISUAL_AND_PHYSICAL_REVIEW",
}
report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
print("CMAI_RETARGET", json.dumps({"blend": str(out), "report": str(report_path), "action": action.name}))
