"""Conservative eight-leg walk from each chain's own rest pose."""
import argparse, json, math, sys
from pathlib import Path

LEGS=['Front.L','Front.R','MidFront.L','MidFront.R','MidRear.L','MidRear.R','Rear.L','Rear.R']
PHASES=[0.0, math.pi, math.pi*.5, math.pi*1.5, math.pi*.25, math.pi*1.25, math.pi*.75, math.pi*1.75]

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--blend',required=True); ap.add_argument('--output',required=True); ap.add_argument('--report',required=True); argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]; a=ap.parse_args(argv)
 import bpy
 from mathutils import Vector
 from creature_motion_ai.ik_step import solve_rest_relative_two_link, world_direction_pose_matrix, restore_terminal_foot_world_orientation
 bpy.ops.wm.open_mainfile(filepath=str(Path(a.blend).resolve())); s=bpy.context.scene; arm=next(o for o in s.objects if o.type=='ARMATURE'); s.frame_set(1); bpy.context.view_layer.update()
 action=bpy.data.actions.new('CMAI_Balisk_EightLeg_Walk'); arm.animation_data_create(); arm.animation_data.action=action; setups=[]; rows=[]
 for leg,phase in zip(LEGS,PHASES):
  chain=[f'Leg_{leg}_{i:02d}' for i in (1,2,3)]
  if any(not arm.pose.bones.get(n) for n in chain): rows.append({'leg':leg,'status':'UNSUPPORTED','reason':'missing_chain'}); continue
  rest={n:arm.matrix_world@arm.pose.bones[n].matrix.copy() for n in chain}; hip=arm.matrix_world@arm.pose.bones[chain[0]].head; knee=arm.matrix_world@arm.pose.bones[chain[0]].tail; ankle=arm.matrix_world@arm.pose.bones[chain[1]].tail; foot=arm.matrix_world@arm.pose.bones[chain[2]].tail; upper=(knee-hip).length; lower=(ankle-knee).length; bend=(knee-hip).cross(ankle-hip).normalized(); setups.append((leg,phase,chain,rest,hip,ankle,foot,upper,lower,bend)); rows.append({'leg':leg,'status':'READY','chain':chain})
 for f in range(1,25):
  q=(f-1)/23; envelope=math.sin(math.pi*q); srows=[]
  for leg,phase,chain,rest,hip,ankle,foot,upper,lower,bend in setups:
   wave=math.sin(2*math.pi*q+phase)
   target=ankle + Vector((0.006*wave*envelope,0,0.004*max(0,wave)*envelope))
   solved=solve_rest_relative_two_link(hip,target,upper,lower,bend,min_knee_angle=math.radians(12))
   if solved.get('status')!='PASS': srows.append({'leg':leg,'status':'REJECTED','reason':solved.get('reason')}); continue
   b1=arm.pose.bones[chain[0]]; b2=arm.pose.bones[chain[1]]; b1.matrix=arm.matrix_world.inverted()@world_direction_pose_matrix(rest[chain[0]],hip,hip,solved['knee'],knee); bpy.context.view_layer.update(); b2.matrix=arm.matrix_world.inverted()@world_direction_pose_matrix(rest[chain[1]],knee,solved['knee'],solved['foot'],ankle); bpy.context.view_layer.update(); restore_terminal_foot_world_orientation(arm,chain[2],rest[chain[2]],arm.matrix_world@b2.tail); bpy.context.view_layer.update()
   for b in (b1,b2,arm.pose.bones[chain[2]]): b.keyframe_insert('rotation_mode',frame=f); (b.keyframe_insert('rotation_quaternion',frame=f) if b.rotation_mode=='QUATERNION' else b.keyframe_insert('rotation_euler',frame=f))
   srows.append({'leg':leg,'status':'ACCEPTED','target':list(target)})
  rows.append({'frame':f,'legs':srows})
 s.frame_start=1; s.frame_end=24; s.render.fps=24; s['CMAI_artistic_mode']='rest_relative_conservative_eight_leg'; bpy.ops.wm.save_as_mainfile(filepath=str(Path(a.output).resolve())); Path(a.report).write_text(json.dumps({'status':'EIGHT_LEG_CONSERVATIVE_GENERATED','action':action.name,'legs':LEGS,'frames':rows,'stride_world':0.006,'lift_world':0.004,'original_assets_preserved':True},indent=2),encoding='utf-8')
if __name__=='__main__': main()
