import bpy, json, sys
from mathutils import Vector

arm=bpy.data.objects.get('CrimsonSpineBehemoth_Rig')
names=['Leg_Front.L_01','Leg_Front.L_02','Leg_Front.L_03']
scene=bpy.context.scene
for f in [1,12,25,41,61,81]:
    scene.frame_set(f); bpy.context.view_layer.update()
    pb=[arm.pose.bones[n] for n in names]
    heads=[tuple((arm.matrix_world@p.head).xyz) for p in pb]
    tails=[tuple((arm.matrix_world@p.tail).xyz) for p in pb]
    print(json.dumps({'frame':f,'heads':heads,'tails':tails,'quats':[tuple(p.rotation_quaternion) for p in pb]}))
