import argparse, subprocess
from pathlib import Path
def main():
 p=argparse.ArgumentParser(); p.add_argument('--blender',required=True); p.add_argument('--blend',required=True); p.add_argument('--report',required=True); a=p.parse_args(); rp=str(Path(a.report).resolve()).replace('\\','/')
 expr=f'''import bpy,json
bpy.ops.wm.open_mainfile(filepath=r"{Path(a.blend).resolve()}"); s=bpy.context.scene; arm=next(o for o in bpy.data.objects if o.type=='ARMATURE'); mesh=next(o for o in bpy.data.objects if o.type=='MESH'); deps=bpy.context.evaluated_depsgraph_get(); names=['Leg_Front.L_01','Leg_Front.L_02','Leg_Front.L_03']; groups={{mesh.vertex_groups[n].index for n in names if mesh.vertex_groups.get(n)}}; ids=[v.index for v in mesh.data.vertices if any(g.group in groups and g.weight>0.25 for g in v.groups)]
def snap(f):
 s.frame_set(f); bpy.context.view_layer.update(); deps.update(); ev=mesh.evaluated_get(deps); me=ev.to_mesh(); vals={{i:list(ev.matrix_world@me.vertices[i].co) for i in ids}}; ev.to_mesh_clear(); bones={{n:list((arm.matrix_world@arm.pose.bones[n].head)) + list((arm.matrix_world@arm.pose.bones[n].tail)) for n in names}}; return vals,bones
v1,b1=snap(1); v24,b24=snap(24); ground=min(x[2] for x in v1.values()); worst=sorted(({{'index':i,'z24':v24[i][2],'z1':v1[i][2],'penetration':ground-v24[i][2],'weights':[{{'group':mesh.vertex_groups[g.group].name,'weight':g.weight}} for g in mesh.data.vertices[i].groups if g.weight>0.05]}} for i in ids if v24[i][2]<ground),key=lambda x:x['penetration'],reverse=True)[:20]
out={{'status':'penetration_traced','ground_z':ground,'candidate_vertex_count':len(ids),'worst_vertices':worst,'bones_frame1':b1,'bones_frame24':b24,'note':'Candidate vertices selected by Front.L leg group weights; full mesh is evaluated through dependency graph.'}}
open(r'{rp}','w').write(json.dumps(out,indent=2)); print(json.dumps(out))'''
 subprocess.run([a.blender,'--background','--python-expr',expr],check=True)
if __name__=='__main__': main()
