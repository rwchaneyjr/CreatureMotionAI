import argparse, subprocess, json
from pathlib import Path

def main():
    p=argparse.ArgumentParser(); p.add_argument('--blender',required=True); p.add_argument('--source',required=True); p.add_argument('--output',required=True); p.add_argument('--report',required=True); a=p.parse_args()
    out=str(Path(a.output).resolve()).replace('\\','/'); rep=str(Path(a.report).resolve()).replace('\\','/')
    expr=f'''import bpy, math, json
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=r"{Path(a.source).resolve()}")
s=bpy.context.scene; s.frame_start=1; s.frame_end=24; s.render.fps=24
arm=next(o for o in bpy.data.objects if o.type=='ARMATURE'); mesh=next(o for o in bpy.data.objects if o.type=='MESH')
legs=['Leg_Front.L','Leg_Front.R','Leg_MidFront.L','Leg_MidFront.R','Leg_MidRear.L','Leg_MidRear.R','Leg_Rear.L','Leg_Rear.R']
for pb in arm.pose.bones:
 for c in list(pb.constraints): pb.constraints.remove(c)
for o in list(bpy.data.objects):
 if o.name.startswith('CMAI_Walk_') or o.name.startswith('CMAI_Normalized_'): bpy.data.objects.remove(o,do_unlink=True)
arm.animation_data_clear()
act=bpy.data.actions.new('CMAI_Normalized_Walk_24F'); act.use_fake_user=True; arm.animation_data_create(); arm.animation_data.action=act
def wp(pb,tail=False): return arm.matrix_world @ (pb.tail if tail else pb.head)
def leglen(n): return sum(arm.data.bones[n+'_0%d'%i].length for i in (1,2,3))
base={{n:wp(arm.pose.bones[n+'_03'],True) for n in legs}}; lens={{n:leglen(n) for n in legs}}; avg=sum(lens.values())/8
body_len=(arm.matrix_world@arm.data.bones['Body_03'].tail-arm.matrix_world@arm.data.bones['Body_01'].head).length
forward=Vector((0,-1,0)); travel=body_len*.10; body_up=avg*.02
items=[]
for idx,n in enumerate(legs):
 hip=wp(arm.pose.bones[n+'_01']); knee=wp(arm.pose.bones[n+'_01'],True); ankle=wp(arm.pose.bones[n+'_02'],True); foot=base[n]; plane=(knee-hip).cross(foot-knee); pole_dir=plane.normalized().cross((knee-hip).normalized()).normalized() if plane.length>1e-6 else Vector((0,0,1))
 t=bpy.data.objects.new('CMAI_Normalized_Target_'+n,None); t.empty_display_type='SPHERE'; t.empty_display_size=.025; t.location=foot; s.collection.objects.link(t)
 q=bpy.data.objects.new('CMAI_Normalized_Pole_'+n,None); q.empty_display_type='CUBE'; q.empty_display_size=.02; q.location=knee+pole_dir*.22; s.collection.objects.link(q)
 c=arm.pose.bones[n+'_03'].constraints.new('IK'); c.name='CMAI_Normalized_IK_'+n; c.target=t; c.pole_target=q; c.chain_count=3; c.influence=1.0
 items.append((n,t,foot,lens[n],idx))
arm.location=(0,0,0); arm.keyframe_insert('location',frame=1); arm.location=forward*travel; arm.keyframe_insert('location',frame=24)
rows=[]
for f in range(1,25):
 u=(f-1)/23.0; root=forward*(travel*u); arm.location=root
 for n,t,basepos,L,idx in items:
  ph=(f-1)/24.0*math.tau+idx*math.pi/4; swing=max(0.0,math.sin(ph)); stride=math.sin(ph)*(.20*L); lift=(swing*swing)*(.10*L)
  # Stance targets remain at their original world contact; swing follows body and advances.
  desired=basepos + (root if swing>0.02 else Vector()) + forward*stride + Vector((0,0,lift))
  hip_now=arm.matrix_world @ arm.data.bones[n+'_01'].head
  reach=0.98*L
  delta=desired-hip_now
  if delta.length>reach: desired=hip_now+delta.normalized()*reach
  t.location=desired; t.keyframe_insert('location',frame=f)
 arm.keyframe_insert('location',frame=f)
s.frame_set(1); bpy.context.view_layer.update()
report={{'status':'normalized_walk_created','frames':24,'fps':24,'body_length':body_len,'travel':travel,'body_vertical':body_up,'leg_lengths':lens,'stride_fraction':.20,'lift_fraction':.10,'forward_axis':'local -Y / world -Y','output':r'{out}'}}
open(r'{rep}','w').write(json.dumps(report,indent=2)); bpy.ops.wm.save_as_mainfile(filepath=r'{out}'); print(json.dumps(report))'''
    r=subprocess.run([a.blender,'--background','--python-expr',expr],capture_output=True,text=True,check=True)
    print(r.stdout[-4000:])
if __name__=='__main__': main()
