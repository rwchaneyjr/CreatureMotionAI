"""Create a sparse, layered, rest-relative FK walking block on the original rig."""
import sys, json, math
from pathlib import Path
import bpy
from mathutils import Vector

LEGS=['Front.L','Front.R','MidFront.L','MidFront.R','MidRear.L','MidRear.R','Rear.L','Rear.R']
# Alternating support groups with quarter-cycle offsets, matching the
# observed animal-like rhythm without assuming hidden-leg identities.
PHASES=[0,math.pi,math.pi*.5,math.pi*1.5,math.pi*.25,math.pi*1.25,math.pi*.75,math.pi*1.75]
KEYS=[1,7,13,19,25]
# Per-leg correction factors.  Front.L is the only chain identified by the
# ground-contact audit as producing a substantial new penetration.  Keeping
# this correction local preserves the other seven trajectories.
AMPLITUDE_SCALE={leg:0.70 for leg in LEGS}
AMPLITUDE_SCALE['Front.L']=0.45
BEND_SCALE={'Front.L':0.10,'Front.R':0.10,'MidFront.L':0.14,'MidFront.R':0.14,'MidRear.L':0.18,'MidRear.R':0.18,'Rear.L':0.18,'Rear.R':0.18}

def main():
    argv=sys.argv[sys.argv.index('--')+1:]; blend,out,report=argv[0:3]
    bpy.ops.wm.open_mainfile(filepath=str(Path(blend).resolve()))
    from creature_motion_ai.ik_step import solve_rest_relative_two_link, world_direction_pose_matrix, restore_terminal_foot_world_orientation
    s=bpy.context.scene; s.frame_start=1; s.frame_end=24; s.render.fps=24; s.frame_set(1)
    arm=bpy.data.objects.get('CrimsonSpineBehemoth_Rig') or next(o for o in bpy.data.objects if o.type=='ARMATURE')
    mesh=bpy.data.objects.get('CrimsonSpineBehemoth_Mesh') or next(o for o in bpy.data.objects if o.type=='MESH')
    action=bpy.data.actions.new('CMAI_Balisk_Layered_FK_Walk'); action.use_fake_user=True
    arm.animation_data_create(); arm.animation_data.action=action
    setups=[]
    for leg,phase in zip(LEGS,PHASES):
        names=[f'Leg_{leg}_{i:02d}' for i in (1,2,3)]; ps=[arm.pose.bones.get(n) for n in names]
        if any(p is None for p in ps): continue
        hip=arm.matrix_world@ps[0].head; knee=arm.matrix_world@ps[0].tail; ankle=arm.matrix_world@ps[1].tail; foot=arm.matrix_world@ps[2].tail
        bend=(knee-hip).cross(ankle-hip)
        if bend.length<1e-7: bend=Vector((0,0,1))
        bend.normalize(); axis=foot-hip; axis.z=0
        if axis.length<1e-7: axis=Vector((0,1,0))
        axis.normalize(); upper=(knee-hip).length; lower=(ankle-knee).length
        rest={n:ps[i].matrix.copy() for i,n in enumerate(names)}
        setups.append((leg,phase,names,hip,knee,ankle,foot,upper,lower,bend,axis,rest))
    rows=[]; inv=arm.matrix_world.inverted()
    for f in KEYS:
        q=(f-1)/24.0; frame=[]
        for leg,phase,names,hip,knee,ankle,foot,upper,lower,bend,axis,rest in setups:
            if f in (1,25):
                for bname in names:
                    b=arm.pose.bones[bname]; b.matrix=rest[bname]; bpy.context.view_layer.update()
                    b.keyframe_insert(data_path='rotation_mode',frame=f)
                    if b.rotation_mode=='QUATERNION': b.keyframe_insert(data_path='rotation_quaternion',frame=f)
                    else: b.keyframe_insert(data_path='rotation_euler',frame=f)
                frame.append({'leg':leg,'status':'REST_KEY'})
                continue
            wave=math.sin(2*math.pi*q+phase); swing=max(0.0,wave); amp=AMPLITUDE_SCALE.get(leg,1.0)
            # Articulated step: stance holds near rest, swing lifts first,
            # advances through the middle of the arc, then replants.
            stride=min(.014,(upper+lower)*.055)*amp
            lift=min(.018,(upper+lower)*.075)*amp
            swing_lift=swing*swing
            desired=ankle+axis*(stride*wave)+Vector((0,0,lift*swing_lift))
            # During swing, shorten the effective target radius slightly so
            # the middle joint visibly folds instead of behaving like a rod.
            if swing_lift > 1e-5:
                desired = hip + (desired-hip) * (1.0 - BEND_SCALE.get(leg,0.10)*swing_lift)
            # Conservative reach repair: shrink only the proposed displacement,
            # never bone lengths or the original rest pose.
            target=desired; solved=None; used_scale=1.0; reject_reason=None
            for scale in (1.0,0.75,0.5,0.25,0.0):
                candidate=ankle+(desired-ankle)*scale
                trial=solve_rest_relative_two_link(hip,candidate,upper,lower,bend,min_knee_angle=math.radians(15))
                if trial.get('status')=='PASS': target,solved,used_scale=candidate,trial,scale; break
                reject_reason=trial.get('reason')
            if solved is None:
                frame.append({'leg':leg,'status':'REJECTED','reason':reject_reason,'fallback':'rest_pose'}); continue
            b1,b2,b3=[arm.pose.bones[n] for n in names]
            b1.matrix=inv@world_direction_pose_matrix(rest[names[0]],hip,hip,solved['knee'],knee); bpy.context.view_layer.update()
            parent_tail=arm.matrix_world@b1.tail
            b2.matrix=inv@world_direction_pose_matrix(rest[names[1]],parent_tail,solved['knee'],solved['foot'],ankle); bpy.context.view_layer.update()
            restore_terminal_foot_world_orientation(arm,names[2],rest[names[2]],arm.matrix_world@b2.tail); bpy.context.view_layer.update()
            for b in (b1,b2,b3):
                b.keyframe_insert(data_path='rotation_mode',frame=f)
                if b.rotation_mode=='QUATERNION': b.keyframe_insert(data_path='rotation_quaternion',frame=f)
                else: b.keyframe_insert(data_path='rotation_euler',frame=f)
            frame.append({'leg':leg,'status':'ACCEPTED','foot_target':list(target),'repair_scale':used_scale,'was_unreachable_at_full_scale':used_scale<1.0})
        rows.append({'frame':f,'legs':frame})
    # Body layer: extremely small bob, keyed sparsely and kept on root only.
    root=arm.pose.bones.get('Root')
    if root:
        base=root.location.copy()
        for f in KEYS:
            root.location=base+Vector((0,0,0.002*math.sin(2*math.pi*(f-1)/24.0)))
            root.keyframe_insert(data_path='location',frame=f)
        root.location=base
    # Tail/head secondary layer is intentionally omitted unless a profile explicitly enables it.
    s['CMAI_animation_mode']='layered_sparse_rest_relative_fk'; s['CMAI_layers']='body,legs,feet'; s['CMAI_source']='original_static_standing.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(out).resolve()))
    before=sum(1 for f in rows for x in f['legs'] if x.get('was_unreachable_at_full_scale'))
    rejected=sum(1 for f in rows for x in f['legs'] if x.get('status')=='REJECTED')
    Path(report).write_text(json.dumps({'status':'LAYERED_FK_BLOCK_GENERATED','action':action.name,'keyframes':KEYS,'legs':len(setups),'frames':rows,'repair':{'full_scale_unreachable_before_repair':before,'rejected_after_repair':rejected,'scales':[1.0,.75,.5,.25,0.0]},'secondary_motion':'body only; head/tail unchanged','original_assets_preserved':True},indent=2),encoding='utf-8')
    print(json.dumps({'output':out,'report':report,'action':action.name,'legs':len(setups)}))
if __name__=='__main__': main()
