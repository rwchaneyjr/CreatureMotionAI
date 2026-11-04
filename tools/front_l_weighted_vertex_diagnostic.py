import argparse, subprocess
from pathlib import Path
def main():
 p=argparse.ArgumentParser(); p.add_argument('--blender',required=True); p.add_argument('--blend',required=True); p.add_argument('--output',required=True); a=p.parse_args(); out=str(Path(a.output).resolve()).replace('\\','/')
 expr=f'''import bpy,json
bpy.ops.wm.open_mainfile(filepath=r"{Path(a.blend).resolve()}"); s=bpy.context.scene; arm=next(o for o in bpy.data.objects if o.type=='ARMATURE'); mesh=next(o for o in bpy.data.objects if o.type=='MESH'); deps=bpy.context.evaluated_depsgraph_get(); names=['Leg_Front.L_01','Leg_Front.L_02','Leg_Front.L_03']; gi={{n:mesh.vertex_groups[n].index for n in names if mesh.vertex_groups.get(n)}}; ids=[v.index for v in mesh.data.vertices if any(g.group in gi.values() and g.weight>.05 for g in v.groups)]
s.frame_set(1); bpy.context.view_layer.update(); ev=mesh.evaluated_get(deps); me=ev.to_mesh(); ground=min((ev.matrix_world@v.co).z for v in me.vertices); ev.to_mesh_clear(); rows=[]
for f in (11,12,13,14):
 s.frame_set(f); bpy.context.view_layer.update(); ev=mesh.evaluated_get(deps); me=ev.to_mesh(); pts={{i:list(ev.matrix_world@me.vertices[i].co) for i in ids}}; ev.to_mesh_clear(); verts=[]
 for i,p in pts.items():
  if p[2]<ground: verts.append({{'index':i,'position':p,'penetration':ground-p[2],'weights':[{{'bone':mesh.vertex_groups[g.group].name,'weight':g.weight}} for g in mesh.data.vertices[i].groups if g.weight>.05]}})
 rows.append({{'frame':f,'penetrating':sorted(verts,key=lambda x:x['penetration'],reverse=True)[:100],'bones':{{n:{{'rot_euler':list(arm.pose.bones[n].rotation_euler),'rot_quat':list(arm.pose.bones[n].rotation_quaternion),'head':list(arm.matrix_world@arm.pose.bones[n].head),'tail':list(arm.matrix_world@arm.pose.bones[n].tail)}} for n in names}},'foot_endpoint':list(arm.matrix_world@arm.pose.bones[names[-1]].tail)}})
open(r'{out}','w').write(json.dumps({{'status':'weighted_vertex_diagnostic_complete','ground_z':ground,'candidate_count':len(ids),'frames':rows}},indent=2)); print(json.dumps({{'status':'weighted_vertex_diagnostic_complete','ground_z':ground,'candidate_count':len(ids),'penetrating_counts':[len(r['penetrating']) for r in rows]}}))'''
 subprocess.run([a.blender,'--background','--python-expr',expr],check=True)
if __name__=='__main__': main()
