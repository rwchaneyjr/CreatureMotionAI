import json, sys, math, bpy
from pathlib import Path
BLEND=sys.argv[-2]; OUT=Path(sys.argv[-1]); OUT.parent.mkdir(parents=True,exist_ok=True)
FRAMES=[27,28,29,67,68,69,107,108,109]
bpy.context.scene.frame_set(1)
scene=bpy.context.scene; arm=next(o for o in scene.objects if o.type=='ARMATURE')
names=['Leg_Rear.R_01','Leg_Rear.R_02','Leg_Rear.R_03','Leg_MidRear.R_01','Leg_MidRear.R_02','Leg_MidRear.R_03']
rest={n:arm.pose.bones[n].rotation_quaternion.copy() for n in names}
rows=[]
for f in FRAMES:
 scene.frame_set(f); bpy.context.view_layer.update(); r={'frame':f}
 for n in names:
  q=arm.pose.bones[n].rotation_quaternion; d=rest[n].rotation_difference(q).angle
  r[n]=math.degrees(d)
 rows.append(r)
OUT.write_text(json.dumps({'blend':BLEND,'frames':rows,'note':'Rotation magnitudes relative to frame 1; not a collision verdict.'},indent=2),encoding='utf-8')
print(json.dumps(rows))
