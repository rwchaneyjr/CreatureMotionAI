import argparse, subprocess
from pathlib import Path
def main():
 p=argparse.ArgumentParser(); p.add_argument('--blender',required=True); p.add_argument('--blend',required=True); p.add_argument('--report',required=True); a=p.parse_args()
 rp=str(Path(a.report).resolve()).replace('\\','/')
 expr=f'''import bpy,json,math
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=r"{Path(a.blend).resolve()}"); s=bpy.context.scene; arm=next(o for o in bpy.data.objects if o.type=='ARMATURE'); mesh=next(o for o in bpy.data.objects if o.type=='MESH'); names=['Leg_Front.L_01','Leg_Front.L_02','Leg_Front.L_03']; idx=set()
for v in mesh.data.vertices:
 if any(g.group in [mesh.vertex_groups.get(n).index for n in names if mesh.vertex_groups.get(n)] and g.weight>0.25 for g in v.groups): idx.add(v.index)
deps=bpy.context.evaluated_depsgraph_get(); s.frame_set(1); bpy.context.view_layer.update(); ev0=mesh.evaluated_get(deps); me0=ev0.to_mesh(); base=[mesh.matrix_world@me0.vertices[i].co for i in idx]; ground=min(v.z for v in base); ev0.to_mesh_clear()
rows=[]
for f in range(1,25):
 s.frame_set(f); bpy.context.view_layer.update(); ev=mesh.evaluated_get(deps); me=ev.to_mesh(); pts=[mesh.matrix_world@me.vertices[i].co for i in idx]; pen=max(0.0,ground-min(v.z for v in pts)); rows.append({{'frame':f,'min_z':min(v.z for v in pts),'penetration':pen,'vertex_count':len(pts)}}); ev.to_mesh_clear()
out={{'status':'front_leg_mesh_validation','weighted_vertex_count':len(idx),'ground_plane_z':ground,'rows':rows,'max_penetration':max(r['penetration'] for r in rows),'affected_frames':[r['frame'] for r in rows if r['penetration']>1e-5],'note':'Vertices selected by Front.L leg vertex-group weights; ground reference is the minimum selected-vertex Z in the original standing pose.'}}
open(r'{rp}','w').write(json.dumps(out,indent=2)); print(json.dumps(out))'''
 subprocess.run([a.blender,'--background','--python-expr',expr],check=True)
if __name__=='__main__': main()
