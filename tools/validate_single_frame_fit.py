"""Bounded validation and approximate reprojection comparison for single-frame candidates."""
import argparse,json,math,sys
from pathlib import Path
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--labels',required=True); ap.add_argument('--original',required=True); ap.add_argument('--candidates',nargs='+',required=True); ap.add_argument('--report',required=True)
 argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]; a=ap.parse_args(argv)
 import bpy
 from mathutils import Vector
 labels=json.loads(Path(a.labels).read_text(encoding='utf-8'))['frames']; ref0=labels['1']; ref=json.loads(Path(a.labels).read_text(encoding='utf-8'))['frames']['26']
 def read(path,frame):
  bpy.ops.wm.open_mainfile(filepath=str(Path(path).resolve())); s=bpy.context.scene; arm=next(o for o in s.objects if o.type=='ARMATURE'); mesh=next(o for o in s.objects if o.type=='MESH'); chain=['Leg_Rear.L_01','Leg_Rear.L_02','Leg_Rear.L_03']; s.frame_set(frame); bpy.context.view_layer.update(); p=[]
  for n in chain: p += [arm.matrix_world@arm.pose.bones[n].head, arm.matrix_world@arm.pose.bones[n].tail]
  joints=[p[0],p[1],p[3],p[5]]; groups={mesh.vertex_groups[n].index for n in chain if mesh.vertex_groups.get(n)}; ids=[v.index for v in mesh.data.vertices if any(g.group in groups and g.weight>.05 for g in v.groups)]; ev=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get()); me=ev.to_mesh(); pts=[ev.matrix_world@me.vertices[i].co for i in ids]; ev.to_mesh_clear(); q=(arm.matrix_world@arm.pose.bones[chain[2]].matrix).to_quaternion(); bend=(joints[1]-joints[0]).cross(joints[3]-joints[0]).normalized(); return joints,pts,q,bend
 rest,restpts,restq,restbend=read(a.original,1); rest2,_,_,_=read(a.original,1); r2d=[ref0[k]['uv'] for k in ('hip','knee','ankle','foot')];
 # Approximate orthographic side map: world X -> image X and world Z -> image Y.
 import numpy as np
 X=np.array([[p.x,1,0,0] for p in rest]+[[p.z,0,1,0] for p in rest],float); y=np.array([q[0] for q in r2d]+[q[1] for q in r2d],float); coef=np.linalg.lstsq(X,y,rcond=None)[0]
 def proj(ps): return [[float(coef[0]*p.x+coef[1]),float(coef[2]*p.z+coef[3])] for p in ps]
 baseerr=sum(math.dist(proj(rest)[i],r2d[i]) for i in range(4))/4; rows=[]
 for path in a.candidates:
  joints,pts,q,bend=read(path,26); p2=proj(joints); err=sum(math.dist(p2[i],r2d[i]) for i in range(4))/4; ground=min(p.z for p in restpts); pen=max(0.,ground-min(p.z for p in pts)); ori=math.degrees(q.rotation_difference(restq).angle); dot=float(bend.dot(restbend)); rows.append({'candidate':str(path),'mean_reprojection_px':err,'baseline_mean_error_px':baseerr,'improvement_px':baseerr-err,'ground_penetration':pen,'foot_orientation_deviation_deg':ori,'bend_alignment_dot':dot,'proxy_collision':'UNVERIFIED','targeted_mesh_collision':'UNVERIFIED','status':'UNVERIFIED'})
 out={'status':'UNVERIFIED_SINGLE_FRAME_VALIDATION','projection':'approximate_world_XZ_orthographic_fit_to_frame_1','candidates':rows,'selected_candidate':'cmai_single_frame_rearL_fit_26.blend','note':'Candidate selection remains subject to visual review; proxy and targeted mesh collision are not claimed as exact mesh clearance.'}; Path(a.report).write_text(json.dumps(out,indent=2),encoding='utf-8'); print(json.dumps(out,indent=2))
if __name__=='__main__': main()
