"""Small rest-relative artistic step; one leg only, no mirrored rotation assumptions."""
import argparse, json, math, sys
from pathlib import Path
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--blend',required=True); ap.add_argument('--output',required=True); ap.add_argument('--report',required=True); argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]; a=ap.parse_args(argv)
 import bpy
 from mathutils import Vector
 from creature_motion_ai.ik_step import solve_rest_relative_two_link, world_direction_pose_matrix, restore_terminal_foot_world_orientation
 bpy.ops.wm.open_mainfile(filepath=str(Path(a.blend).resolve())); s=bpy.context.scene; arm=next(o for o in s.objects if o.type=='ARMATURE'); chain=['Leg_Rear.L_01','Leg_Rear.L_02','Leg_Rear.L_03']; s.frame_set(1); bpy.context.view_layer.update()
 rest={n:arm.matrix_world@arm.pose.bones[n].matrix.copy() for n in chain}; hip=arm.matrix_world@arm.pose.bones[chain[0]].head; knee=arm.matrix_world@arm.pose.bones[chain[0]].tail; ankle=arm.matrix_world@arm.pose.bones[chain[1]].tail; foot=arm.matrix_world@arm.pose.bones[chain[2]].tail; upper=(knee-hip).length; lower=(ankle-knee).length; bend=(knee-hip).cross(ankle-hip).normalized(); action=bpy.data.actions.new('CMAI_RestRelative_Artistic_RearL_24F'); arm.animation_data_create(); arm.animation_data.action=action
 rows=[]
 for f in range(1,25):
  q=(f-1)/23; env=math.sin(math.pi*q); target=ankle+arm.matrix_world.to_3x3()@Vector((0.0,0.015*math.sin(2*math.pi*q),-0.01*env)); solved=solve_rest_relative_two_link(hip,target,upper,lower,bend,min_knee_angle=math.radians(12));
  if solved.get('status')!='PASS': rows.append({'frame':f,'status':'REJECTED','reason':solved.get('reason')}); continue
  b1=arm.pose.bones[chain[0]]; b2=arm.pose.bones[chain[1]]; b1.matrix=arm.matrix_world.inverted()@world_direction_pose_matrix(rest[chain[0]],hip,hip,solved['knee'],knee); bpy.context.view_layer.update(); b2.matrix=arm.matrix_world.inverted()@world_direction_pose_matrix(rest[chain[1]],knee,solved['knee'],solved['foot'],ankle); bpy.context.view_layer.update(); restore_terminal_foot_world_orientation(arm,chain[2],rest[chain[2]],arm.matrix_world@b2.tail); bpy.context.view_layer.update()
  for b in (b1,b2,arm.pose.bones[chain[2]]): b.keyframe_insert('rotation_mode',frame=f); (b.keyframe_insert('rotation_quaternion',frame=f) if b.rotation_mode=='QUATERNION' else b.keyframe_insert('rotation_euler',frame=f))
  rows.append({'frame':f,'status':'ACCEPTED','target':list(target),'knee':list(solved['knee']),'ankle':list(solved['foot'])})
 s.frame_start=1; s.frame_end=24; s.render.fps=24; s['CMAI_artistic_mode']='rest_relative_conservative_one_leg'; bpy.ops.wm.save_as_mainfile(filepath=str(Path(a.output).resolve())); Path(a.report).write_text(json.dumps({'status':'ONE_LEG_CONSERVATIVE_TEST','action':action.name,'chain':chain,'frames':rows,'stride_world':0.015,'lift_world':0.01,'other_legs_animated':False},indent=2),encoding='utf-8')
if __name__=='__main__': main()
