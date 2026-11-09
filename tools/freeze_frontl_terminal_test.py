import bpy, sys
from pathlib import Path

blend, out_blend = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=str(Path(blend).resolve()))
s=bpy.context.scene; arm=bpy.data.objects['CrimsonSpineBehemoth_Rig']
names=['Leg_Front.L_01','Leg_Front.L_02','Leg_Front.L_03']
s.frame_set(1); bpy.context.view_layer.update()
rest={n:arm.pose.bones[n].matrix.copy() for n in names}
s.frame_set(12); bpy.context.view_layer.update()
# Keep the terminal segment in the exact evaluated rest orientation while
# retaining the solved upstream pose. This is a diagnostic, not a final gait.
arm.pose.bones[names[2]].matrix = rest[names[2]]
bpy.context.view_layer.update()
for n in names:
    p=arm.pose.bones[n]
    p.keyframe_insert(data_path='rotation_mode', frame=12)
    if p.rotation_mode == 'QUATERNION':
        p.keyframe_insert(data_path='rotation_quaternion', frame=12)
    else:
        p.keyframe_insert(data_path='rotation_euler', frame=12)
s.frame_set(25); bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(Path(out_blend).resolve()))
print('saved', out_blend)
