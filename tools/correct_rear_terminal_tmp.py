import bpy, sys, json
from pathlib import Path
BLEND=sys.argv[-2]; OUT=Path(sys.argv[-1]); OUT.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)
scene=bpy.context.scene
arm=next(o for o in scene.objects if o.type=='ARMATURE')
act=arm.animation_data.action
bone=arm.pose.bones['Leg_MidRear.R_03']
samples={}
for frame in range(1,122):
    scene.frame_set(frame); bpy.context.view_layer.update(); samples[frame]=bone.rotation_quaternion.copy()
base=samples[1]
new=act.copy(); new.name=act.name+'_RearTerminalReduced25'
arm.animation_data.action=new
for frame,q in samples.items():
    # component-space reduction around the standing quaternion, then normalize
    nq=base.copy(); nq.x=base.x+0.75*(q.x-base.x); nq.y=base.y+0.75*(q.y-base.y); nq.z=base.z+0.75*(q.z-base.z); nq.w=base.w+0.75*(q.w-base.w); nq.normalize()
    scene.frame_set(frame); bone.rotation_mode='QUATERNION'; bone.rotation_quaternion=nq
    bone.keyframe_insert(data_path='rotation_quaternion',frame=frame,index=-1)
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
print(json.dumps({'source_action':act.name,'duplicate_action':new.name,'blend':str(OUT),'reduced_bone':'Leg_MidRear.R_03','factor':0.75}))
