"""Combine side/front camera fits into one separate Blender scene."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("blend", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--blender", type=Path, required=True)
    parser.add_argument("--side-distance", type=float, default=3.0)
    parser.add_argument("--side-height", type=float, default=0.0)
    parser.add_argument("--front-distance", type=float, default=4.2)
    parser.add_argument("--front-height", type=float, default=0.45)
    args = parser.parse_args()
    expr = f"""import bpy
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=r'{args.blend.resolve()}')
scene=bpy.context.scene
def make(name, location):
    data=bpy.data.cameras.get(name) or bpy.data.cameras.new(name)
    obj=bpy.data.objects.get(name) or bpy.data.objects.new(name, data)
    if obj.name not in [o.name for o in scene.objects]: bpy.context.collection.objects.link(obj)
    obj.location=location
    obj.rotation_euler=(Vector((0,0,0))-obj.location).to_track_quat('-Z','Y').to_euler()
    obj.data.lens=52.0
    return obj
side=make('CMAI_Calibrated_Side_Camera', (-{args.side_distance},0,{args.side_height}))
front=make('CMAI_Calibrated_Front_Camera', (0,-{args.front_distance},{args.front_height}))
scene.camera=side
scene['cmai_calibrated_cameras']='side_and_front'
scene['cmai_original_asset_preserved']=True
bpy.ops.wm.save_as_mainfile(filepath=r'{args.output.resolve()}')
print('CMAI_CAMERAS', side.name, front.name)
"""
    args.output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(args.blender), "--background", "--python-expr", expr], check=True)
    print({"output": str(args.output), "side_distance": args.side_distance, "front_distance": args.front_distance})


if __name__ == "__main__":
    main()
