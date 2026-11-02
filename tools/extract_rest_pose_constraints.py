"""Extract rest-pose lengths and conservative joint limits from the original rig."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("blend", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--blender", type=Path, required=True)
    args = parser.parse_args()
    expr = f"""import bpy, json
bpy.ops.wm.open_mainfile(filepath=r'{args.blend.resolve()}')
arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
bones={{}}
for b in arm.data.bones:
    bones[b.name]={{'length':float(b.length),'head':list(b.head_local),'tail':list(b.tail_local),'parent':b.parent.name if b.parent else None,'use_deform':bool(b.use_deform)}}
result={{'source':r'{args.blend.resolve()}','armature':arm.name,'bone_count':len(bones),'bones':bones,'limits':{{'leg_max_delta_degrees':25.0,'foot_pitch_min_degrees':-15.0,'foot_pitch_max_degrees':15.0,'root_max_translation':0.08}},'note':'Limits are conservative diagnostics; rest pose remains authoritative.'}}
open(r'{args.output.resolve()}','w',encoding='utf-8').write(json.dumps(result,indent=2))
print('CMAI_CONSTRAINTS',len(bones))
"""
    args.output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(args.blender), "--background", "--python-expr", expr], check=True)
    print({"output": str(args.output)})


if __name__ == "__main__":
    main()
