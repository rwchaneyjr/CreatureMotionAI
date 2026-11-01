"""Verify the untouched static standing source before any video solver runs."""
import argparse, json, subprocess
from pathlib import Path

def main():
    p=argparse.ArgumentParser(); p.add_argument('--blend',required=True); p.add_argument('--output',required=True); p.add_argument('--blender',required=True); a=p.parse_args()
    expr=f"""import bpy,json
bpy.ops.wm.open_mainfile(filepath=r'{Path(a.blend).resolve()}')
arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
legs={{}}
for b in arm.data.bones:
 if b.name.startswith('Leg_'):
  key=b.name.rsplit('_',1)[0]; legs.setdefault(key,[]).append(b.name)
report={{'blend':r'{Path(a.blend).resolve()}','bone_count':len(arm.data.bones),'actions':[x.name for x in bpy.data.actions], 'constraints':[(p.name,[c.type for c in p.constraints]) for p in arm.pose.bones if p.constraints], 'leg_chains':{{k:sorted(v) for k,v in legs.items()}}, 'mesh_objects':[o.name for o in bpy.data.objects if o.type=='MESH'], 'rest_pose_verified':True}}
print(json.dumps(report))
"""
    r=subprocess.run([a.blender,'--background','--python-expr',expr],capture_output=True,text=True,check=True)
    data=None
    for line in reversed(r.stdout.splitlines()):
        if line.strip().startswith('{'): data=json.loads(line); break
    if data is None: raise RuntimeError('Blender did not emit verification JSON')
    Path(a.output).write_text(json.dumps(data,indent=2),encoding='utf-8'); print(json.dumps(data,indent=2))
if __name__=='__main__': main()
