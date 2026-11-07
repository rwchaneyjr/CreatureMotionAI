import bpy, json, sys
from pathlib import Path

argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
def arg(n,d):
    try:
        return argv[argv.index(n)+1]
    except ValueError:
        return d
src=Path(arg('--source',r'C:\Users\rober\Desktop\cmai_balisk_eight_leg_walk_repaired_clean.blend'))
target=next((o for o in bpy.data.objects if o.type=='ARMATURE'),None)
if not target: raise RuntimeError('No imported target armature')
with bpy.data.libraries.load(str(src),link=False) as (df,dt):
    dt.objects=[n for n in df.objects if n=='CrimsonSpineBehemoth_Rig']
ref=next((o for o in dt.objects if o and o.type=='ARMATURE'),None)
if not ref: raise RuntimeError('Reference armature missing')
rows=[]
for name,b in target.data.bones.items():
    rb=ref.data.bones.get(name)
    if not rb:
        rows.append({'bone':name,'status':'MISSING_IN_REFERENCE'}); continue
    th=target.matrix_world@b.head_local; tt=target.matrix_world@b.tail_local
    rh=ref.matrix_world@rb.head_local; rt=ref.matrix_world@rb.tail_local
    rows.append({'bone':name,'head_error':(th-rh).length,'tail_error':(tt-rt).length,'length_target':b.length,'length_reference':rb.length,'bone_matrix_target':[[round(x,6) for x in row] for row in b.matrix_local],'bone_matrix_reference':[[round(x,6) for x in row] for row in rb.matrix_local]})
report={'status':'COMPATIBILITY_DIAGNOSTIC','target_armature':target.name,'reference_armature':ref.name,'bones':rows,'max_head_error':max((r.get('head_error',0) for r in rows),default=0),'max_tail_error':max((r.get('tail_error',0) for r in rows),default=0),'note':'Matching names are insufficient; rest transforms and bone rolls must match before reusing quaternion Action curves.'}
out=Path(arg('--out','data/generated/fbx_action_compatibility_report.json')).resolve(); out.write_text(json.dumps(report,indent=2),encoding='utf-8'); print(json.dumps({k:report[k] for k in ('status','max_head_error','max_tail_error')}))
