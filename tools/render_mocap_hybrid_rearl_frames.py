"""Render the copied single-leg test without changing its saved rig or Action."""
import os
from pathlib import Path

import bpy


source = Path(os.environ["CMAI_HYBRID_BLEND"])
destination = Path(os.environ["CMAI_HYBRID_COMPARISON_RENDER"])
destination.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(source.resolve()))
scene = bpy.context.scene
scene.render.resolution_x = 640
scene.render.resolution_y = 360
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
for frame in range(1, 33):
    scene.frame_set(frame)
    scene.render.filepath = str(destination / f"frame_{frame:02}.png")
    bpy.ops.render.render(write_still=True)
print("Rendered 32 original-camera frames to", destination)
