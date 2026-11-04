import argparse, subprocess
from pathlib import Path
def main():
 p=argparse.ArgumentParser(); p.add_argument('--blender',required=True); p.add_argument('--source',required=True); p.add_argument('--animated',required=True); p.add_argument('--output',required=True); a=p.parse_args(); out=str(Path(a.output).resolve()).replace('\\','/')
 expr=f'''import bpy,json
from mathutils import Vector
def load(path): bpy.ops.wm.open_mainfile(filepath=path)
load(r"{Path(a.source).resolve()}"); arm=next(o for o in bpy.data.objects if o.type=='ARMATURE'); mesh=next(o for o in bpy.data.objects if o.type=='MESH'); names=['Leg_Front.L_01','Leg_Front.L_02','Leg_Front.L_03']; chain=[]
for n in names:
 b=arm.data.bones[n]; chain.append({{'name':n,'parent':b.parent.name if b.parent else None,'length':b.length,'head':list(b.head),'tail':list(b.tail),'matrix_local':[list(r) for r in b.matrix_local]}})
deps=bpy.context.evaluated_depsgraph_get(); s=bpy.context.scene; s.frame_set(1); bpy.context.view_layer.update(); ev=mesh.evaluated_get(deps); me=ev.to_mesh(); resting_min=min((ev.matrix_world@v.co).z for v in me.vertices); ev.to_mesh_clear(); ground_objects=[o.name for o in s.objects if o.type in ['MESH','PLANE'] and 'ground' in o.name.lower()]
load(r"{Path(a.animated).resolve()}"); arm=next(o for o in bpy.data.objects if o.type=='ARMATURE'); mesh=next(o for o in bpy.data.objects if o.type=='MESH'); rows=[]
for f in (11,12,13,14):
 s=bpy.context.scene; s.frame_set(f); bpy.context.view_layer.update(); deps=bpy.context.evaluated_depsgraph_get(); ev=mesh.evaluated_get(deps); me=ev.to_mesh(); pts=[ev.matrix_world@me.vertices[i].co for i in range(len(me.vertices))]; idx=sorted(range(len(pts)),key=lambda i:pts[i].z)[:10]; ev.to_mesh_clear(); p=arm.pose.bones['Leg_Front.L_03']; foot=list(arm.matrix_world@p.tail); rows.append(dict(frame=f,lowest_vertices=[dict(index=i,position=list(pts[i])) for i in idx],foot_endpoint=foot))
out={{'status':'chain_ground_diagnostic_complete','chain':chain,'bone_count':len(arm.data.bones),'resting_mesh_min_z':resting_min,'ground_objects_in_original':ground_objects,'animated_frames':rows,'conclusion':'Ground reference is original resting evaluated mesh minimum; penetrating vertices require weight-group tracing to classify exact Front.L influence.'}}
open(r'{out}','w').write(json.dumps(out,indent=2)); print(json.dumps({{'status':out['status'],'resting_mesh_min_z':resting_min,'chain':chain}}))'''
 subprocess.run([a.blender,'--background','--python-expr',expr],check=True)
if __name__=='__main__': main()
