"""Create a tiny one-leg-at-a-time diagnostic Action from the clean baseline."""
import argparse, json, math
from pathlib import Path
import bpy

LEGS=("Leg_Front.L","Leg_Front.R","Leg_MidFront.L","Leg_MidFront.R","Leg_MidRear.L","Leg_MidRear.R","Leg_Rear.L","Leg_Rear.R")

def key(rig, frame):
    for b in rig.pose.bones:
        b.keyframe_insert('location',frame=frame,group=b.name)
        if b.rotation_mode=='QUATERNION': b.keyframe_insert('rotation_quaternion',frame=frame,group=b.name)
        else: b.keyframe_insert('rotation_euler',frame=frame,group=b.name)
        b.keyframe_insert('scale',frame=frame,group=b.name)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--source',required=True); p.add_argument('--output',required=True); p.add_argument('--degrees',type=float,default=2.0); a=p.parse_args()
    bpy.ops.wm.open_mainfile(filepath=str(Path(a.source).resolve()))
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    if rig.animation_data: rig.animation_data.action=None
    action=bpy.data.actions.new('CMAI_One_Leg_Micro_Tests'); action.use_fake_user=True; rig.animation_data_create(); rig.animation_data.action=action
    frame=1; key(rig,frame)
    for leg in LEGS:
        frame += 2
        bone=rig.pose.bones.get(leg+'_01')
        if bone:
            bone.rotation_mode='XYZ'; bone.rotation_euler.y += math.radians(a.degrees)
        key(rig,frame)
        frame += 1
        if bone: bone.rotation_euler.y -= math.radians(a.degrees)
        key(rig,frame)
    bpy.context.scene.frame_start=1; bpy.context.scene.frame_end=frame
    rig['cmai_action_source']='clean_rest_baseline_24.blend'; rig['cmai_motion_status']='micro_leg_diagnostic_only'
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(a.output).resolve()))
    print(json.dumps({'output':str(a.output),'frames':frame,'legs_tested':len(LEGS)}))
if __name__=='__main__': main()
