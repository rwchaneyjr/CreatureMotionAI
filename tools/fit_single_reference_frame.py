"""Bounded single-frame existing-mesh pose fit from verified 2D Rear.L labels."""
import argparse,json,math,sys
from pathlib import Path
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--blend',required=True); ap.add_argument('--labels',required=True); ap.add_argument('--output',required=True); ap.add_argument('--report',required=True); ap.add_argument('--scale',type=float,default=1.0)
 argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]; a=ap.parse_args(argv)
 import bpy
 from mathutils import Vector
 from creature_motion_ai.ik_step import solve_rest_relative_two_link,world_direction_pose_matrix,restore_terminal_foot_world_orientation
 labels=json.loads(Path(a.labels).read_text(encoding='utf-8'))['frames']; f0=labels['1']; f1=labels['26'];
 if any(f0[k].get('state')!='manual_verified' or f1[k].get('state')!='manual_verified' for k in ('hip','knee','ankle','foot')): raise RuntimeError('required labels are not manually verified')
 bpy.ops.wm.open_mainfile(filepath=str(Path(a.blend).resolve())); s=bpy.context.scene; arm=next(o for o in s.objects if o.type=='ARMATURE'); chain=['Leg_Rear.L_01','Leg_Rear.L_02','Leg_Rear.L_03']; s.frame_set(1); bpy.context.view_layer.update(); rest={n:arm.matrix_world@arm.pose.bones[n].matrix.copy() for n in chain}; hip=arm.matrix_world@arm.pose.bones[chain[0]].head; knee=arm.matrix_world@arm.pose.bones[chain[0]].tail; ankle=arm.matrix_world@arm.pose.bones[chain[1]].tail; foot=arm.matrix_world@arm.pose.bones[chain[2]].tail; upper=(knee-hip).length; lower=(ankle-knee).length; bend=(knee-hip).cross(ankle-hip).normalized()
 pix_len=math.dist(f0['hip']['uv'],f0['foot']['uv']); world_len=(foot-hip).length; scale=world_len/max(pix_len,1e-6); dx=(f1['foot']['uv'][0]-f0['foot']['uv'][0])*scale*a.scale; dz=-(f1['foot']['uv'][1]-f0['foot']['uv'][1])*scale*a.scale; max_disp=0.35*(upper+lower); d=Vector((dx,0,dz));
 if d.length>max_disp: d.normalize(); d*=max_disp
 target=ankle+d
 # Keep the image-guided displacement inside the original chain workspace;
 # this is a bounded model-fit diagnostic, not an unrestricted 3D solve.
 reach=(target-hip).length; max_reach=upper+lower-1e-4
 if reach>max_reach: target=hip+(target-hip).normalized()*max_reach
 solved=solve_rest_relative_two_link(hip,target,upper,lower,bend,min_knee_angle=math.radians(12));
 if solved.get('status')!='PASS': raise RuntimeError(str(solved))
 action=bpy.data.actions.new('CMAI_SingleFrame_RearL_Fit_26'); arm.animation_data_create(); arm.animation_data.action=action; b1=arm.pose.bones[chain[0]]; b2=arm.pose.bones[chain[1]]; b1.matrix=arm.matrix_world.inverted()@world_direction_pose_matrix(rest[chain[0]],hip,hip,solved['knee'],knee); bpy.context.view_layer.update(); b2.matrix=arm.matrix_world.inverted()@world_direction_pose_matrix(rest[chain[1]],knee,solved['knee'],solved['foot'],ankle); bpy.context.view_layer.update(); restore_terminal_foot_world_orientation(arm,chain[2],rest[chain[2]],arm.matrix_world@b2.tail); bpy.context.view_layer.update()
 for b in (b1,b2,arm.pose.bones[chain[2]]): b.keyframe_insert('rotation_mode',frame=1); b.keyframe_insert('rotation_mode',frame=26); (b.keyframe_insert('rotation_quaternion',frame=1) if b.rotation_mode=='QUATERNION' else b.keyframe_insert('rotation_euler',frame=1)); (b.keyframe_insert('rotation_quaternion',frame=26) if b.rotation_mode=='QUATERNION' else b.keyframe_insert('rotation_euler',frame=26))
 s.frame_start=1; s.frame_end=26; bpy.ops.wm.save_as_mainfile(filepath=str(Path(a.output).resolve())); Path(a.report).write_text(json.dumps({'status':'SINGLE_FRAME_EXISTING_MESH_FIT','reference_frame':26,'labels_verified':True,'chain':chain,'pixel_scale_world_per_px':scale,'applied_foot_delta_world':list(d),'analytical_knee':list(solved['knee']),'analytical_ankle':list(solved['foot']),'camera':'APPROXIMATE_SIDE_VIEW','depth':'HELD_AT_REST','confidence':'APPROXIMATE_NOT_METRIC','action':action.name},indent=2),encoding='utf-8')
if __name__=='__main__': main()
