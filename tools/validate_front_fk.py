import argparse, subprocess
from pathlib import Path
def main():
 p=argparse.ArgumentParser(); p.add_argument('--blender',required=True); p.add_argument('--blend',required=True); p.add_argument('--report',required=True); a=p.parse_args(); rp=str(Path(a.report).resolve()).replace('\\','/')
 expr=f'''import bpy,json
bpy.ops.wm.open_mainfile(filepath=r"{Path(a.blend).resolve()}"); s=bpy.context.scene; arm=next(o for o in bpy.data.objects if o.type=='ARMATURE'); mesh=next(o for o in bpy.data.objects if o.type=='MESH'); deps=bpy.context.evaluated_depsgraph_get(); gs={{mesh.vertex_groups[n].index for n in ['Leg_Front.L_01','Leg_Front.L_02','Leg_Front.L_03'] if mesh.vertex_groups.get(n)}}; ids=[v.index for v in mesh.data.vertices if any(g.group in gs and g.weight>.25 for g in v.groups)]
def snap():
 e=mesh.evaluated_get(deps); m=e.to_mesh(); z=[(e.matrix_world@m.vertices[i].co).z for i in ids]; e.to_mesh_clear(); return min(z),max(z)
s.frame_set(1); bpy.context.view_layer.update(); deps.update(); g,_=snap(); rows=[]
for f in range(1,25): s.frame_set(f); bpy.context.view_layer.update(); deps.update(); z0,z1=snap(); rows.append({{'frame':f,'min_z':z0,'penetration':max(0,g-z0)}})
out={{'status':'front_fk_validation','weighted_vertices':len(ids),'ground_z':g,'max_penetration':max(r['penetration'] for r in rows),'rows':rows,'action':arm.animation_data.action.name if arm.animation_data and arm.animation_data.action else None}}
open(r'{rp}','w').write(json.dumps(out,indent=2)); print(json.dumps(out))'''
 subprocess.run([a.blender,'--background',a.blend,'--python-expr',expr],check=True)
if __name__=='__main__': main()
