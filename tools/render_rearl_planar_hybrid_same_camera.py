"""Render saved Rear.L Actions under one camera without changing source files."""
import argparse
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--planar", type=Path, required=True)
    parser.add_argument("--hybrid", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    args.output.mkdir(parents=True, exist_ok=True)
    for label, source in (("planar", args.planar), ("hybrid", args.hybrid)):
        bpy.ops.wm.open_mainfile(filepath=str(source.resolve()))
        scene = bpy.context.scene
        cam = bpy.data.objects.get("CMAI_RearL_Matched_Side")
        if cam is None:
            data = bpy.data.cameras.new("CMAI_RearL_Matched_Side")
            cam = bpy.data.objects.new(data.name, data)
            scene.collection.objects.link(cam)
        cam.location = Vector((3.0, -0.82, 0.11))
        cam.rotation_euler = (Vector((0.0, -0.82, 0.11)) - cam.location).to_track_quat("-Z", "Y").to_euler()
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = 2.0
        scene.camera = cam
        scene.render.engine = "BLENDER_WORKBENCH"
        scene.display.shading.color_type = "TEXTURE"
        scene.display.shading.background_type = "VIEWPORT"
        scene.display.shading.background_color = (0.93, 0.93, 0.93)
        scene.render.resolution_x = 640
        scene.render.resolution_y = 360
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = "PNG"
        for frame in (1, 12, 18, 24):
            scene.frame_set(frame)
            scene.render.filepath = str((args.output / f"{label}_{frame:02}.png").resolve())
            bpy.ops.render.render(write_still=True)
    print(f"Rendered matched camera frames to {args.output}")


if __name__ == "__main__":
    main()
