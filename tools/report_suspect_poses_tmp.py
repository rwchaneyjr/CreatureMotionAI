import bpy,json,math
from pathlib import Path
from mathutils import Vector

bpy.ops.wm.open_mainfile(filepath=r'C:\Users\rober\CreatureMotionAI\data\generated\e2e_balisk_test\builder\seamless\seamless_loop.blend')
s=bpy.context.scene; arm=next(o for o in s.objects if o.type=='ARMATURE')
rows=[]
for f in [1,27,28,29,67,68,69,107,108,109]:
    s.frame_set(f); bpy.context.view_layer.update(); row={'frame':f}
    for leg in ['Rear.R','MidRear.R']:
        p=[arm.pose.bones[f'Leg_{leg}_{i:02d}'] for i in (1,2,3)]
        pts=[arm.matrix_world@p[0].head,arm.matrix_world@p[1].head,arm.matrix_world@p[2].head,arm.matrix_world@p[2].tail]
        row[leg]={'hip':list(pts[0]),'knee':list(pts[1]),'ankle':list(pts[2]),'foot':list(pts[3]),'knee_angle_deg':math.degrees((pts[0]-pts[1]).angle(pts[2]-pts[1]))}
    rows.append(row)
Path(r'C:\Users\rober\CreatureMotionAI\data\generated\e2e_balisk_test\builder\suspected_collision\suspect_pose_report.json').write_text(json.dumps(rows,indent=2))
print(json.dumps(rows[1:4]))
