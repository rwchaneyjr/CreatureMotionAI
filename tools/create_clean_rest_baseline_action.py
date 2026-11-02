"""Create a new short Action that keys the original rest pose only."""
import argparse, json
from pathlib import Path
import bpy

def main():
    p=argparse.ArgumentParser(); p.add_argument('--source',required=True); p.add_argument('--output',required=True); p.add_argument('--start',type=int,default=1); p.add_argument('--end',type=int,default=24); a=p.parse_args()
    bpy.ops.wm.open_mainfile(filepath=str(Path(a.source).resolve()))
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    if rig.animation_data: rig.animation_data.action=None
    action=bpy.data.actions.new('CMAI_Clean_Rest_Baseline_24f'); action.use_fake_user=True
    rig.animation_data_create(); rig.animation_data.action=action
    for frame in range(a.start,a.end+1):
        bpy.context.scene.frame_set(frame)
        for b in rig.pose.bones:
            b.keyframe_insert('location',frame=frame,group=b.name)
            if b.rotation_mode=='QUATERNION': b.keyframe_insert('rotation_quaternion',frame=frame,group=b.name)
            else: b.keyframe_insert('rotation_euler',frame=frame,group=b.name)
            b.keyframe_insert('scale',frame=frame,group=b.name)
    bpy.context.scene.frame_start=a.start; bpy.context.scene.frame_end=a.end
    rig['cmai_action_source']='original_static_standing.blend'; rig['cmai_motion_status']='clean_rest_baseline_only'
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(a.output).resolve()))
    print(json.dumps({'output':str(a.output),'action':action.name,'frames':a.end-a.start+1}))
if __name__=='__main__': main()
