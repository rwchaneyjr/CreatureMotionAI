import bpy, json, math
from pathlib import Path
from mathutils import Vector

path=r'C:\Users\rober\CreatureMotionAI\data\generated\e2e_balisk_test\builder\seamless\seamless_loop.blend'
bpy.ops.wm.open_mainfile(filepath=path)
s=bpy.context.scene; arm=next(o for o in s.objects if o.type=='ARMATURE')
legs=['Front.L','Front.R','MidFront.L','MidFront.R','MidRear.L','MidRear.R','Rear.L','Rear.R']
rest={}
s.frame_set(1); bpy.context.view_layer.update()
for leg in legs:
    n=[f'Leg_{leg}_{i:02d}' for i in (1,2,3)]; p=[arm.pose.bones[x] for x in n]
    a,b,c=arm.matrix_world@p[0].head,arm.matrix_world@p[1].head,arm.matrix_world@p[2].head
    rest[leg]=(a,b,c,(b-a).cross(c-a).normalized())
rows=[]
for f in range(1,122):
    s.frame_set(f); bpy.context.view_layer.update()
    for leg in legs:
        n=[f'Leg_{leg}_{i:02d}' for i in (1,2,3)]; p=[arm.pose.bones[x] for x in n]
        a,b,c=arm.matrix_world@p[0].head,arm.matrix_world@p[1].head,arm.matrix_world@p[2].head
        bend=(b-a).cross(c-a).normalized().dot(rest[leg][3])
        rows.append({'frame':f,'leg':leg,'bend_dot':float(bend),'knee_angle_deg':float(math.degrees((a-b).angle(c-b)))})
worst=sorted(rows,key=lambda x:x['bend_dot'])[:20]
out=Path(r'C:\Users\rober\CreatureMotionAI\data\generated\e2e_balisk_test\builder\knee_direction_diagnostic.json')
out.write_text(json.dumps({'worst':worst,'by_leg':{leg:min(r['bend_dot'] for r in rows if r['leg']==leg) for leg in legs}},indent=2))
print(json.dumps({'worst':worst[:8],'by_leg':{leg:min(r['bend_dot'] for r in rows if r['leg']==leg) for leg in legs}}))
