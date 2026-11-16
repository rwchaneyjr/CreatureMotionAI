import bpy,sys,json
from pathlib import Path
BLEND=sys.argv[-2]; OUT=Path(sys.argv[-1]); OUT.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)
s=bpy.context.scene; arm=next(o for o in s.objects if o.type=='ARMATURE'); act=arm.animation_data.action
names=['Leg_Rear.R_01','Leg_Rear.R_02','Leg_MidRear.R_01','Leg_MidRear.R_02']
samples={}
for f in range(1,122):
    s.frame_set(f); bpy.context.view_layer.update(); samples[f]={n:arm.pose.bones[n].rotation_quaternion.copy() for n in names}
base=samples[1]; new=act.copy(); new.name=act.name+'_RightFullChainCorrection'; arm.animation_data.action=new
for f,qs in samples.items():
    s.frame_set(f)
    for n,q in qs.items():
        b=base[n]; nq=b.copy(); nq.x=b.x+0.80*(q.x-b.x); nq.y=b.y+0.80*(q.y-b.y); nq.z=b.z+0.80*(q.z-b.z); nq.w=b.w+0.80*(q.w-b.w); nq.normalize(); p=arm.pose.bones[n]; p.rotation_mode='QUATERNION'; p.rotation_quaternion=nq; p.keyframe_insert(data_path='rotation_quaternion',frame=f,index=-1)
bpy.context.view_layer.update(); bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
print(json.dumps({'source_action':act.name,'duplicate_action':new.name,'factor':0.8,'bones':names}))
