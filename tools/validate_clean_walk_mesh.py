import bpy,json,sys
from pathlib import Path
from mathutils import Vector
argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
def arg(n,d):
    try:return argv[argv.index(n)+1]
    except ValueError:return d
out=Path(arg('--out','data/generated/cmai_clean_walk_mesh_validation.json')).resolve()
scene=bpy.context.scene
for o in bpy.data.objects:
    if o.get('cmai_proxy') or o.name.startswith(('CMAI_PROXY','CMAI_')):
        o.hide_viewport=True; o.hide_render=True
arm=next((o for o in bpy.data.objects if o.type=='ARMATURE'),None)
mesh=next((o for o in bpy.data.objects if o.type=='MESH' and not o.name.startswith('CMAI_')),None)
action=next((a for a in bpy.data.actions if a.name=='CMAI_Balisk_EightLeg_Walk'),None)
if arm and action: arm.animation_data_create(); arm.animation_data.action=action
def verts(f):
    scene.frame_set(f); dg=bpy.context.evaluated_depsgraph_get(); ev=mesh.evaluated_get(dg); me=ev.to_mesh(); mw=ev.matrix_world; p=[mw@v.co for v in me.vertices]; ev.to_mesh_clear(); return p
base=verts(1); rows=[]
for f in (1,6,12,18,24):
    p=verts(f); ds=[(a-b).length for a,b in zip(p,base)]; rows.append({'frame':f,'max_vertex_displacement':max(ds),'mean_vertex_displacement':sum(ds)/len(ds)})
out.write_text(json.dumps({'status':'MESH_EVALUATION_CHECK','mesh':mesh.name if mesh else None,'action':action.name if action else None,'vertex_count':len(base),'frames':rows,'note':'Frame 1 is the baseline of the saved Action; this does not prove full collision clearance.'},indent=2),encoding='utf-8')
print(json.dumps(rows))
