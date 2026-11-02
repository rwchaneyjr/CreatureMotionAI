"""Create a non-destructive Blender scene showing bounded IK targets."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("blend", type=Path)
    parser.add_argument("candidates", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--blender", type=Path, required=True)
    args = parser.parse_args()
    candidates = json.loads(args.candidates.read_text(encoding="utf-8"))
    frame_literal = repr(candidates.get("frames", []))
    expr = f"""import bpy
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=r'{args.blend.resolve()}')
scene=bpy.context.scene
arm=next(o for o in scene.objects if o.type=='ARMATURE')
arm.show_in_front=True; arm.data.show_names=True; arm.data.display_type='OCTAHEDRAL'
for frame in {frame_literal}:
    for leg, item in frame.get('legs', {{}}).items():
        if item.get('state') != 'candidate': continue
        name='CMAI_Diagnostic_Target_'+leg
        obj=bpy.data.objects.get(name) or bpy.data.objects.new(name,None)
        if obj.name not in [o.name for o in scene.objects]: bpy.context.collection.objects.link(obj)
        obj.empty_display_type='SPHERE'; obj.empty_display_size=0.06; obj.color=(1.0,0.2,0.05,1.0)
        obj.location=Vector(item['foot_target'])
scene['cmai_diagnostic_only']=True
scene['cmai_bone_rotations_written']=False
bpy.ops.wm.save_as_mainfile(filepath=r'{args.output.resolve()}')
"""
    args.output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(args.blender), "--background", "--python-expr", expr], check=True)
    print({"output": str(args.output), "diagnostic_only": True})


if __name__ == "__main__":
    main()
