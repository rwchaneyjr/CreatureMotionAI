import argparse, subprocess
from pathlib import Path
def main():
 p=argparse.ArgumentParser(); p.add_argument('--blender',required=True); p.add_argument('--blend',required=True); p.add_argument('--output',required=True); a=p.parse_args(); out=str(Path(a.output).resolve()).replace('\\','/')
 expr=f'''import bpy,json,math,time
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=r"{Path(a.blend).resolve()}"); s=bpy.context.scene; arm=next(o for o in bpy.data.objects if o.type=='ARMATURE'); mesh=next(o for o in bpy.data.objects if o.type=='MESH'); deps=bpy.context.evaluated_depsgraph_get(); n='Leg_Front.L'; groups={{mesh.vertex_groups[x].index for x in [n+'_01',n+'_02',n+'_03'] if mesh.vertex_groups.get(x)}}; ids=[v.index for v in mesh.data.vertices if any(g.group in groups and g.weight>.25 for g in v.groups)]; s.frame_set(1); bpy.context.view_layer.update(); ev=mesh.evaluated_get(deps); me=ev.to_mesh(); ground=min((ev.matrix_world@me.vertices[i].co).z for i in ids); ev.to_mesh_clear(); rows=[]; t0=time.perf_counter()
for f in range(1,25):
 s.frame_set(f); bpy.context.view_layer.update(); ev=mesh.evaluated_get(deps); me=ev.to_mesh(); pts=[ev.matrix_world@me.vertices[i].co for i in ids]; z=min(p.z for p in pts); ev.to_mesh_clear(); rows.append({{'frame':f,'min_z':z,'penetration':max(0,ground-z),'proxy_points':len(pts)}})
dt=time.perf_counter()-t0
out={{'status':'fast_proxy_complete','proxy_type':'Front.L weighted-vertex clearance proxy','weighted_vertices':len(ids),'ground_z':ground,'runtime_seconds':dt,'runtime_per_frame':dt/24,'rows':rows,'max_penetration':max(r['penetration'] for r in rows),'self_collision':'COARSE_PROXY_NOT_FULL_BVH','collision_pairs':[],'collision_pair_schema':{{'frame':None,'region_a':None,'region_b':None,'bones_a':[],'bones_b':[],'triangle_ids_a':[],'triangle_ids_b':[],'location':None,'adjacent_or_expected_contact':None}},'note':'Original mesh and rig untouched; this proxy is a fast clearance gate, not a replacement for detailed BVH. Collision pairs are empty unless a region-aware proxy is supplied.'}}
open(r'{out}','w').write(json.dumps(out,indent=2)); print(json.dumps(out))'''
 subprocess.run([a.blender,'--background',a.blend,'--python-expr',expr],check=True)
if __name__=='__main__': main()
