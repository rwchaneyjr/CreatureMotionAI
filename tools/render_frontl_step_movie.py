import bpy, sys
from pathlib import Path
from mathutils import Vector

blend, out_blend, out_movie = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=str(Path(blend).resolve()))
s = bpy.context.scene
arm = bpy.data.objects.get('CrimsonSpineBehemoth_Rig')
if not arm or not arm.animation_data or not arm.animation_data.action:
    raise RuntimeError('Front.L step Action not found')
for layer in arm.animation_data.action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for fc in bag.fcurves:
                if not fc.modifiers:
                    fc.modifiers.new('CYCLES')
cam = bpy.data.objects.get('CMAI_FrontL_Step_Camera')
if cam is None:
    data = bpy.data.cameras.new('CMAI_FrontL_Step_Camera')
    cam = bpy.data.objects.new('CMAI_FrontL_Step_Camera', data)
    s.collection.objects.link(cam)
cam.location = (3.2, -0.82, 0.38)
cam.rotation_euler = (Vector((0.0, -0.82, -0.12)) - cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 0.72; s.camera = cam
s.frame_start = 1; s.frame_end = 120; s.render.fps = 24
s.render.engine = 'BLENDER_WORKBENCH'
s.render.resolution_x = 960; s.render.resolution_y = 540; s.render.resolution_percentage = 100
frames = Path(out_movie).resolve().with_suffix('')
frames.mkdir(parents=True, exist_ok=True)
s.render.image_settings.file_format = 'PNG'
s.render.filepath = str(frames / 'frame_')
bpy.ops.wm.save_as_mainfile(filepath=str(Path(out_blend).resolve()))
bpy.ops.render.render(animation=True)
print(f'RENDERED {out_movie}')
