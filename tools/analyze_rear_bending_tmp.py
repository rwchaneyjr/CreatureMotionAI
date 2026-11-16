import bpy, json, math
from pathlib import Path
from mathutils import Vector

blend=r'C:\Users\rober\CreatureMotionAI\data\generated\e2e_balisk_test\builder\seamless\seamless_loop.blend'
out=Path(r'C:\Users\rober\CreatureMotionAI\data\generated\e2e_balisk_test\builder\bending_diagnosis')
out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=blend)
s=bpy.context.scene; arm=next(o for o in s.objects if o.type=='ARMATURE')
legs=['Rear.R','MidRear.R']; rows=[]; rest={}
s.frame_set(1); bpy.context.view_layer.update()
for leg in legs:
    rest[leg]=[]
    for i in (1,2,3):
        p=arm.pose.bones[f'Leg_{leg}_{i:02d}']; rest[leg].append({'rot':p.rotation_quaternion.copy(),'head':arm.matrix_world@p.head,'tail':arm.matrix_world@p.tail})
for f in range(1,121):
    s.frame_set(f); bpy.context.view_layer.update(); row={'frame':f}
    for leg in legs:
        joints=[]; bones=[]
        for i in (1,2,3):
            p=arm.pose.bones[f'Leg_{leg}_{i:02d}']; joints += [arm.matrix_world@p.head] if i<3 else [arm.matrix_world@p.head,arm.matrix_world@p.tail]
            rr=rest[leg][i-1]['rot']; delta=rr.rotation_difference(p.rotation_quaternion)
            bones.append({'name':p.name,'angle_deg':math.degrees(delta.angle),'axis_local':list(delta.axis)})
        angle=math.degrees((joints[0]-joints[1]).angle(joints[2]-joints[1]))
        bend=(joints[1]-joints[0]).cross(joints[2]-joints[0]).normalized()
        row[leg]={'joints':[list(v) for v in joints],'knee_angle_deg':angle,'bend_normal':list(bend),'bones':bones}
    rows.append(row)
summary={leg:{'max_knee_angle_deg':max(r[leg]['knee_angle_deg'] for r in rows),'min_knee_angle_deg':min(r[leg]['knee_angle_deg'] for r in rows),'max_bone_rotation_deg':{f'Leg_{leg}_{i:02d}':max(r[leg]['bones'][i-1]['angle_deg'] for r in rows) for i in (1,2,3)}} for leg in legs}
Path(out/'rear_bending_trajectory.json').write_text(json.dumps({'summary':summary,'frames':rows},indent=2),encoding='utf-8')
print(json.dumps(summary))
