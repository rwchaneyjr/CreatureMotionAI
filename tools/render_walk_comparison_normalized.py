"""Render one saved Balisk walk with the common comparison camera.

Run with Blender background on a COPY-in-memory only: this script changes
scene camera/render settings but never saves the source .blend file.
"""
import json
import sys
from pathlib import Path

import bpy
from mathutils import Euler

args = sys.argv[sys.argv.index("--") + 1:]
out_dir = Path(args[0]).resolve()
out_dir.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
camera = scene.camera
if camera is None:
    raise RuntimeError("Scene has no active camera")

# Canonical view copied from the full-body contact-lock comparison camera.
camera.animation_data_clear()
camera.parent = None
for constraint in list(camera.constraints):
    camera.constraints.remove(constraint)

def set_comparison_camera():
    camera.location = (-3.0, -0.1, 0.04)
    camera.rotation_mode = "XYZ"
    camera.rotation_euler = Euler((1.5575, 0.0, -1.5375), "XYZ")
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 2.35
    camera.data.shift_x = 0.0
    camera.data.shift_y = 0.0

set_comparison_camera()
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.render.engine = "BLENDER_EEVEE"
scene.frame_start = 1
scene.frame_end = 120
scene.render.fps = 24
scene.render.filepath = str(out_dir / "frame_")
scene.render.use_file_extension = True

rig = next((o for o in bpy.data.objects if o.type == "ARMATURE" and
            o.name == "CrimsonSpineBehemoth_Rig"), None)
action_rows = []
if rig and rig.animation_data and rig.animation_data.action:
    action = rig.animation_data.action
    action_rows.append({"name": action.name, "frame_range": list(action.frame_range),
                        "layered": bool(getattr(action, "is_action_layered", False)),
                        "layers": [layer.name for layer in getattr(action, "layers", [])]})

bone_samples = {}
if rig:
    for frame in range(1, 121):
        scene.frame_set(frame)
        set_comparison_camera()
        bpy.context.view_layer.update()
        for bone in rig.pose.bones:
            # Pose-space head/tail include evaluated animation and hierarchy.
            head = rig.matrix_world @ bone.head
            tail = rig.matrix_world @ bone.tail
            row = bone_samples.setdefault(bone.name, {"head": [], "tail": []})
            row["head"].append([round(float(v), 6) for v in head])
            row["tail"].append([round(float(v), 6) for v in tail])

meta = {
    "source_blend": bpy.data.filepath,
    "scene": scene.name,
    "action": action_rows,
    "frame_range": [1, 120], "fps": 24,
    "camera": {"name": camera.name, "type": camera.data.type,
               "location": list(camera.location), "rotation_euler": list(camera.rotation_euler),
               "ortho_scale": camera.data.ortho_scale,
               "resolution": [1280, 720]},
    "bone_world_samples": bone_samples,
}
(out_dir / "render_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
if "--metadata-only" not in args:
    for frame in range(1, 121):
        scene.frame_set(frame)
        set_comparison_camera()
        scene.render.filepath = str(out_dir / f"frame_{frame:04d}.png")
        bpy.ops.render.render(write_still=True)
