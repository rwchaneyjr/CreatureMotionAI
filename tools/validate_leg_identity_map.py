"""Validate that the identity map resolves to the original armature exactly."""
import argparse, json
from pathlib import Path
import bpy

def main():
    p=argparse.ArgumentParser(); p.add_argument('--blend',required=True); p.add_argument('--map',required=True); p.add_argument('--output',required=True); a=p.parse_args()
    data=json.loads(Path(a.map).read_text(encoding='utf-8'))
    bpy.ops.wm.open_mainfile(filepath=str(Path(a.blend).resolve()))
    rigs=[o for o in bpy.data.objects if o.type=='ARMATURE']
    if not rigs: raise RuntimeError('No armature found')
    rig=max(rigs,key=lambda o:len(o.data.bones))
    names={b.name for b in rig.data.bones}
    rows=[]; missing=[]
    for leg in data['legs']:
        absent=[b for b in leg['bones'] if b not in names]; missing.extend(absent)
        rows.append({'id':leg['id'],'name':leg['name'],'bones':leg['bones'],'resolved':not absent,'missing':absent})
    report={'status':'PASS' if not missing and len(data['legs'])==8 else 'FAIL','armature':rig.name,'bone_count':len(names),'expected_leg_count':8,'legs':rows,'missing_bones':missing,'policy':data.get('overlap_policy')}
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2),encoding='utf-8'); print(json.dumps(report,indent=2))
if __name__=='__main__': main()
