import bpy
from pathlib import Path

src = Path(r'C:\Users\rober\Desktop\CMAI_latest_working_animation_copy.blend')
dst = Path(r'C:\Users\rober\Desktop\CMAI_latest_working_animation_copy_no_bone_labels.blend')

for obj in bpy.data.objects:
    if obj.type == 'ARMATURE':
        obj.show_name = False
        obj.show_in_front = True
        obj.display_type = 'WIRE'
        obj.data.display_type = 'BBONE'
        obj.data.axes_position = 0
        for bone in obj.data.bones:
            bone.hide = False

# Hide diagnostic proxy objects and their labels without touching the source mesh.
for obj in bpy.data.objects:
    if obj.get('cmai_proxy') or obj.name.startswith(('CMAI_PROXY', 'CMAI_')):
        obj.hide_viewport = True
        obj.hide_render = True

bpy.ops.wm.save_as_mainfile(filepath=str(dst))
print(f'SAVED {dst}')
