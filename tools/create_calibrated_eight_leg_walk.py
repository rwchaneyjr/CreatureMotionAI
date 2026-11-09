"""Generate a bounded eight-leg walk from per-chain rest geometry.

This is deliberately separate from the retired world-axis gait generator.
Each chain gets its own horizontal travel axis, bend normal, reach, and foot
orientation captured from the original evaluated rest pose.
"""
import argparse, json, math, sys
from pathlib import Path

LEGS = ['Front.L','Front.R','MidFront.L','MidFront.R','MidRear.L','MidRear.R','Rear.L','Rear.R']
PHASES = [0.0, math.pi, math.pi*.5, math.pi*1.5, math.pi*.25, math.pi*1.25, math.pi*.75, math.pi*1.75]

def main():
    p=argparse.ArgumentParser(); p.add_argument('--blend',required=True); p.add_argument('--output',required=True); p.add_argument('--report',required=True); p.add_argument('--limits',default=None)
    p.add_argument('--stride',type=float,default=0.012); p.add_argument('--lift',type=float,default=0.010)
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]; a=p.parse_args(argv)
    import bpy
    from mathutils import Vector
    from creature_motion_ai.ik_step import solve_rest_relative_two_link, world_direction_pose_matrix, restore_terminal_foot_world_orientation
    try:
        from creature_motion_ai.joint_limits import load_profile, clamp_euler
    except ModuleNotFoundError:
        import importlib.util
        spec=importlib.util.spec_from_file_location('cmai_joint_limits', Path(__file__).resolve().parent.parent/'creature_motion_ai'/'joint_limits.py')
        mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        load_profile, clamp_euler=mod.load_profile, mod.clamp_euler
    limits=load_profile(a.limits)
    bpy.ops.wm.open_mainfile(filepath=str(Path(a.blend).resolve()))
    s=bpy.context.scene; arm=next(o for o in s.objects if o.type=='ARMATURE'); s.frame_set(1); bpy.context.view_layer.update()
    action=bpy.data.actions.new('CMAI_Balisk_Calibrated_Walk'); action.use_fake_user=True; arm.animation_data_create(); arm.animation_data.action=action
    setups=[]; calibration=[]; rows=[]
    for leg,phase in zip(LEGS,PHASES):
        chain=[f'Leg_{leg}_{i:02d}' for i in (1,2,3)]
        if any(not arm.pose.bones.get(n) for n in chain): rows.append({'leg':leg,'status':'UNSUPPORTED'}); continue
        ps=[arm.pose.bones[n] for n in chain]
        hip=arm.matrix_world@ps[0].head; knee=arm.matrix_world@ps[0].tail; ankle=arm.matrix_world@ps[1].tail; foot=arm.matrix_world@ps[2].tail
        # Travel follows the leg's own rest foot direction projected onto the ground.
        axis=foot-hip; axis.z=0
        if axis.length<1e-7: axis=Vector((0,1,0))
        axis.normalize()
        bend=(knee-hip).cross(ankle-hip)
        if bend.length<1e-7: bend=Vector((0,0,1))
        bend.normalize();
        upper=(knee-hip).length; lower=(ankle-knee).length
        rest={n:arm.matrix_world@ps[i].matrix.copy() for i,n in enumerate(chain)}
        setup=(leg,phase,chain,rest,hip,ankle,foot,upper,lower,bend,axis)
        setups.append(setup)
        calibration.append({'leg':leg,'chain':chain,'axis_world':list(axis),'bend_normal_world':list(bend),'upper_length':upper,'lower_length':lower,'rest_foot':list(foot),'stride_limit':min(a.stride,(upper+lower)*0.06),'lift_limit':min(a.lift,(upper+lower)*0.05)})
    for f in range(1,25):
        q=(f-1)/23.0; env=math.sin(math.pi*q); frame_rows=[]
        for leg,phase,chain,rest,hip,ankle,foot,upper,lower,bend,axis in setups:
            wave=math.sin(2*math.pi*q+phase)
            swing=max(0.0,wave)
            stride=min(a.stride,(upper+lower)*0.06); lift=min(a.lift,(upper+lower)*0.05)
            target=ankle + axis*(stride*wave*env) + Vector((0,0,lift*swing*env))
            solved=solve_rest_relative_two_link(hip,target,upper,lower,bend,min_knee_angle=math.radians(12))
            if solved.get('status')!='PASS': frame_rows.append({'leg':leg,'status':'REJECTED','reason':solved.get('reason')}); continue
            inv=arm.matrix_world.inverted(); b1=arm.pose.bones[chain[0]]; b2=arm.pose.bones[chain[1]]
            b1.matrix=inv@world_direction_pose_matrix(rest[chain[0]],hip,hip,solved['knee'],knee); bpy.context.view_layer.update()
            solved_parent_tail=arm.matrix_world@b1.tail
            b2.matrix=inv@world_direction_pose_matrix(rest[chain[1]],solved_parent_tail,solved['knee'],solved['foot'],ankle); bpy.context.view_layer.update()
            restore_terminal_foot_world_orientation(arm,chain[2],rest[chain[2]],arm.matrix_world@b2.tail); bpy.context.view_layer.update()
            for b in (b1,b2,arm.pose.bones[chain[2]]):
                if b.rotation_mode == 'XYZ':
                    clamp_euler(b.rotation_euler, b.name, limits)
                b.keyframe_insert('rotation_mode',frame=f)
                if b.rotation_mode=='QUATERNION': b.keyframe_insert('rotation_quaternion',frame=f)
                else: b.keyframe_insert('rotation_euler',frame=f)
            frame_rows.append({'leg':leg,'status':'ACCEPTED','target':list(target),'swing':swing})
        rows.append({'frame':f,'legs':frame_rows})
    s.frame_start=1; s.frame_end=24; s.render.fps=24; s['CMAI_gait_mode']='calibrated_rest_relative_per_leg'; s['CMAI_calibrated_legs']=len(setups)
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); bpy.ops.wm.save_as_mainfile(filepath=str(out))
    Path(a.report).write_text(json.dumps({'status':'CALIBRATED_GAIT_GENERATED','action':action.name,'calibration':calibration,'frames':rows,'joint_limits':limits,'original_assets_preserved':True,'note':'Per-leg rest-derived axes; physical collision validation remains required.'},indent=2),encoding='utf-8')
    print(json.dumps({'output':str(out),'legs':len(setups),'frames':24}))
if __name__=='__main__': main()
