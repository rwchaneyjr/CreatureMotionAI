import bpy
bpy.ops.wm.open_mainfile(filepath=r'C:\Users\rober\CreatureMotionAI\data\generated\pinocchio_midrearL_dramatic_step.blend')
a=bpy.data.objects['CrimsonSpineBehemoth_Rig']; s=bpy.context.scene
print('action',a.animation_data.action.name if a.animation_data and a.animation_data.action else None)
print('slots',len(a.animation_data.action.slots) if a.animation_data and a.animation_data.action else None)
for f in [1,30,60,90,120]:
 s.frame_set(f); bpy.context.view_layer.update(); p=a.pose.bones['Leg_MidRear.L_03']; print(f, list(p.rotation_quaternion), list(a.matrix_world@p.tail))
