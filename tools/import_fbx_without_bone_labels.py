import bpy
from pathlib import Path

fbx = Path(r'C:\Users\rober\Desktop\MESH2MOTION_FBX_TEXTURES\CrimsonSpineBehemoth\CrimsonSpineBehemoth_Animated.fbx')
out = Path(r'C:\Users\rober\CreatureMotionAI\data\generated\CrimsonSpineBehemoth_Animated_no_bone_labels.blend')

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(fbx), automatic_bone_orientation=False)

for obj in bpy.data.objects:
    if obj.type == 'ARMATURE':
        obj.show_name = False
        obj.show_in_front = True
        obj.display_type = 'WIRE'
        obj.data.display_type = 'BBONE'
        for bone in obj.data.bones:
            bone.hide = False
    if obj.get('cmai_proxy') or obj.name.startswith(('CMAI_PROXY', 'CMAI_')):
        obj.hide_viewport = True
        obj.hide_render = True

bpy.ops.wm.save_as_mainfile(filepath=str(out))
print(f'SAVED {out}')
