import bpy, json, sys
from pathlib import Path
from mathutils import Vector

paths = [Path(p) for p in sys.argv[1:] if p.lower().endswith('.blend')]
out = Path(r'C:\Users\rober\CreatureMotionAI\data\generated\bending_history_comparison.json')
legs = ['Leg_Rear.R_01','Leg_Rear.R_02','Leg_Rear.R_03','Leg_MidRear.R_01','Leg_MidRear.R_02','Leg_MidRear.R_03']
result = {}
for path in paths:
    bpy.ops.wm.open_mainfile(filepath=str(path))
    s=bpy.context.scene
    arm=next((o for o in s.objects if o.type=='ARMATURE'),None)
    if not arm: continue
    data={'file':str(path),'frames':{},'max_rotation_deg':{}}
    for f in [1,7,14,21,28,35,41]:
        s.frame_set(f); bpy.context.view_layer.update(); fr={}
        for n in legs:
            p=arm.pose.bones.get(n)
            if not p: continue
            tail=arm.matrix_world @ p.tail
            fr[n]={'tail_world':[round(x,7) for x in tail], 'rotation_quat':[round(x,7) for x in p.rotation_quaternion]}
            data['max_rotation_deg'][n]=max(data['max_rotation_deg'].get(n,0.0), float(p.rotation_quaternion.angle*180/3.141592653589793))
        data['frames'][str(f)]=fr
    result[path.name]=data
out.write_text(json.dumps(result,indent=2))
print(out)
