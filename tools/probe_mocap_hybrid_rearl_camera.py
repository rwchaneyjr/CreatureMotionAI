"""Read-only camera probe for a copied hybrid pose; no .blend is saved."""
import os
from pathlib import Path

import bpy
from mathutils import Vector


source = Path(os.environ["CMAI_HYBRID_BLEND"])
output = Path(os.environ["CMAI_HYBRID_CAMERA_PROBE"])
output.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(source.resolve()))
scene = bpy.context.scene
scene.frame_set(18)
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.image_settings.file_format = "PNG"
camera = scene.camera
for name, location, look_at in (
    ("three_quarter_low", (3.0, -1.7, 0.55), (0, -0.6, 0.02)),
    ("three_quarter_high", (3.0, -2.3, 1.2), (0, -0.6, 0.02)),
):
    camera.location = Vector(location)
    camera.rotation_euler = (Vector(look_at) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.ortho_scale = 2.2
    scene.render.filepath = str(output / f"{name}.png")
    bpy.ops.render.render(write_still=True)
print("Camera probe complete; source .blend unchanged")
