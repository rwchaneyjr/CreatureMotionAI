"""Fast evaluated-mesh and rest-relative checks for the eight-leg proof."""
import argparse,json,math,sys
from pathlib import Path
LEGS=['Front.L','Front.R','MidFront.L','MidFront.R','MidRear.L','MidRear.R','Rear.L','Rear.R']
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--blend',required=True); ap.add_argument('--report',required=True); argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]; a=ap.parse_args(argv)
 import bpy
 from mathutils import Vector
 bpy.ops.wm.open_mainfile(filepath=str(Path(a.blend).resolve())); s=bpy.context.scene; arm=next(o for o in s.objects if o.type=='ARMATURE'); mesh=next(o for o in s.objects if o.type=='MESH'); deps=bpy.context.evaluated_depsgraph_get()
 info={}
 for leg in LEGS:
  ch=[f'Leg_{leg}_{i:02d}' for i in (1,2,3)]; groups={mesh.vertex_groups[n].index for n in ch if mesh.vertex_groups.get(n)}; ids=[v.index for v in mesh.data.vertices if any(g.group in groups and g.weight>.05 for g in v.groups)]; s.frame_set(1); bpy.context.view_layer.update(); ev=mesh.evaluated_get(deps); me=ev.to_mesh(); pts=[ev.matrix_world@me.vertices[i].co for i in ids]; ev.to_mesh_clear(); info[leg]={'chain':ch,'ids':ids,'rest_pts':pts,'ground':min((p.z for p in pts),default=0.),'rest_foot_q':(arm.matrix_world@arm.pose.bones[ch[2]].matrix).to_quaternion() if arm.pose.bones.get(ch[2]) else None}
 rows=[]
 for f in range(1,25):
  s.frame_set(f); bpy.context.view_layer.update(); ev=mesh.evaluated_get(deps); me=ev.to_mesh(); mw=ev.matrix_world; alllegs=[]
  for leg in LEGS:
   x=info[leg]; pts=[mw@me.vertices[i].co for i in x['ids']]; pen=max(0.,x['ground']-min((p.z for p in pts),default=x['ground'])); disp=max(((p-q).length for p,q in zip(pts,x['rest_pts'])),default=0.); ch=x['chain']; b1=arm.pose.bones.get(ch[0]); foot=arm.pose.bones.get(ch[2]); ori=math.degrees((arm.matrix_world@foot.matrix).to_quaternion().rotation_difference(x['rest_foot_q']).angle) if foot else 0.; hip=arm.matrix_world@b1.head; knee=arm.matrix_world@b1.tail; tail=arm.matrix_world@foot.tail; restn=(Vector(x['rest_pts'][0])-Vector(x['rest_pts'][0])).normalized() if False else (arm.matrix_world@b1.tail-hip).cross(tail-hip); dot=1.0 if restn.length<1e-9 else float(restn.normalized().dot(restn.normalized())); alllegs.append({'leg':leg,'penetration':pen,'max_mesh_displacement':disp,'orientation_deg':ori,'bend_check':'UNVERIFIED'})
  ev.to_mesh_clear(); rows.append({'frame':f,'legs':alllegs})
 maxpen=max(v['penetration'] for r in rows for v in r['legs']); moved={leg:max(v['max_mesh_displacement'] for r in rows for v in r['legs'] if v['leg']==leg) for leg in LEGS}; out={'status':'PASS_WITH_LIMITATIONS' if maxpen<=.005 and all(v>1e-4 for v in moved.values()) else 'FAIL','action':arm.animation_data.action.name if arm.animation_data and arm.animation_data.action else None,'frames':rows,'max_ground_penetration':maxpen,'mesh_movement_by_leg':moved,'proxy_collision':'SEE cmai_collision_proxy_report.json','full_mesh_self_collision':'NOT_PERFORMED','note':'Bend direction is reported by proxy/action generation and requires visual review; this validator does not claim anatomical clearance.'}; Path(a.report).write_text(json.dumps(out,indent=2),encoding='utf-8'); print(json.dumps({'status':out['status'],'max_pen':maxpen,'moved':moved}))
if __name__=='__main__': main()
