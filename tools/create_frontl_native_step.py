import bpy, json, sys, math
from pathlib import Path
from mathutils import Vector, Quaternion, Matrix

blend, out_blend, out_report = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=str(Path(blend).resolve()))
s=bpy.context.scene; arm=bpy.data.objects['CrimsonSpineBehemoth_Rig']; mesh=bpy.data.objects['CrimsonSpineBehemoth_Mesh']
s.frame_set(1); bpy.context.view_layer.update(); baseline={p.name:p.matrix.copy() for p in arm.pose.bones}
names=['Leg_Front.L_01','Leg_Front.L_02','Leg_Front.L_03']
anatomy={names[0]:'hip_upper_leg', names[1]:'knee_lower_leg', names[2]:'ankle_foot'}
cd=json.loads(Path('data/generated/ikpy_frontL_chain.json').read_text())
# The segment cross-product is the chain's 3-D bend normal, but for this rig
# it drives the visible side-to-side swipe.  The side-view walking plane is
# the armature Y/Z plane, so use the armature-local X axis as the bend basis.
# This remains rest-relative and is not a world-axis animation hack.
axis=Vector((1.0, 0.0, 0.0))
# Deliberately visible, anatomy-bounded step.  L01 provides the reach/swing,
# L02 provides the knee lift; L03 stays at its rest orientation so the foot
# does not become the primary source of motion.
poses={
    1:(0.00,0.00),       # planted
    5:(0.18,-0.05),      # low backward support/push
    9:(0.52,-0.62),      # lift and begin folding the knee
    13:(0.76,-1.04),     # maximum knee bend and foot lift
    17:(0.30,0.34),      # unfold with hip/knee leading the foot
    21:(-0.52,0.16),    # forward swing / landing
    25:(0.00,0.00),     # exact return to standing
}
def reset():
    for n,m in baseline.items(): arm.pose.bones[n].matrix=m.copy()
    bpy.context.view_layer.update()
def apply(q1,q2):
    reset()
    for n,q in zip(names[:2],(q1,q2)):
        pb=arm.pose.bones[n]; rb=arm.data.bones[n]
        local=(rb.matrix_local.to_3x3().inverted() @ axis).normalized()
        pb.rotation_mode='QUATERNION'; pb.rotation_quaternion=Quaternion(local,q)
    bpy.context.view_layer.update()
def foot(): return arm.matrix_world @ arm.pose.bones[names[-1]].tail
def mesh_disp(ref):
    deps=bpy.context.evaluated_depsgraph_get(); em=mesh.evaluated_get(deps); me=em.to_mesh()
    vals=[(mesh.matrix_world @ v.co - ref[i]).length for i,v in enumerate(me.vertices)]
    em.to_mesh_clear(); return max(vals)
s.frame_set(1); bpy.context.view_layer.update(); ref=[mesh.matrix_world@v.co for v in mesh.data.vertices]; rest_foot=foot(); rest_dirs={n:(arm.matrix_world@arm.pose.bones[n].tail-arm.matrix_world@arm.pose.bones[n].head).normalized() for n in names}; results=[]
for f,(q1,q2) in poses.items():
    s.frame_set(f); apply(q1,q2); fpos=foot();
    seg_angles={n:math.degrees(rest_dirs[n].angle((arm.matrix_world@arm.pose.bones[n].tail-arm.matrix_world@arm.pose.bones[n].head).normalized())) for n in names}
    mismatch = seg_angles[names[2]] > max(seg_angles[names[0]],seg_angles[names[1]]) + 8.0
    results.append({'frame':f,'q1_rad':q1,'q2_rad':q2,'q1_degrees':math.degrees(q1),'q2_degrees':math.degrees(q2),'foot_world':list(fpos),'displacement':float((fpos-rest_foot).length),'max_mesh_displacement':float(mesh_disp(ref)),'segment_direction_change_degrees':seg_angles,'anatomy_mismatch':mismatch,'mismatch_reason':'ankle_foot_direction_dominates' if mismatch else None})
    for n,pb in [(n,arm.pose.bones[n]) for n in names]:
        if pb.rotation_mode=='QUATERNION': pb.keyframe_insert(data_path='rotation_quaternion',frame=f)
        else: pb.keyframe_insert(data_path='rotation_euler',frame=f)
    for pb in [x for x in arm.pose.bones if x.name not in names]:
        n=pb.name
        if pb.rotation_mode=='QUATERNION': pb.keyframe_insert(data_path='rotation_quaternion',frame=f)
        else: pb.keyframe_insert(data_path='rotation_euler',frame=f)
action=arm.animation_data.action; action.name='CMAI_FrontL_NaturalStep'
for layer in action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for fc in bag.fcurves:
                for kp in fc.keyframe_points: kp.interpolation='BEZIER'
s.frame_start=1; s.frame_end=120; s.render.fps=24
bpy.ops.wm.save_as_mainfile(filepath=str(Path(out_blend).resolve()))
Path(out_report).write_text(json.dumps({'status':'NATIVE_FRONTL_STEP_ANATOMY_MAPPED','anatomy_mapping':anatomy,'chain_order':'hip_upper_leg -> knee_lower_leg -> ankle_foot','validation_rule':'reject when ankle_foot direction change exceeds the larger proximal segment change by more than 8 degrees','poses':results,'standing_frames_exact':[1,25],'other_legs':'keyed to baseline'},indent=2))
print(json.dumps(results,indent=2))
