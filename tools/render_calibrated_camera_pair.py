"""Render the unchanged standing pose from calibrated side/front cameras."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("blend", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--blender", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    expr = f"""import bpy
bpy.ops.wm.open_mainfile(filepath=r'{args.blend.resolve()}')
scene=bpy.context.scene
scene.render.engine='BLENDER_WORKBENCH'
scene.render.resolution_x=640; scene.render.resolution_y=360; scene.render.resolution_percentage=100
for name, filename in [('CMAI_Calibrated_Side_Camera','standing_side.png'),('CMAI_Calibrated_Front_Camera','standing_front.png')]:
    scene.camera=bpy.data.objects[name]
    scene.frame_set(1)
    scene.render.filepath=r'{args.output_dir.resolve()}/'+filename
    bpy.ops.render.render(write_still=True)
"""
    subprocess.run([str(args.blender), "--background", "--python-expr", expr], check=True)
    print({"output_dir": str(args.output_dir), "renders": ["standing_side.png", "standing_front.png"]})


if __name__ == "__main__":
    main()
