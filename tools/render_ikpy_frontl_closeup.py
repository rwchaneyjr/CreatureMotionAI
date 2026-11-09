import bpy, sys
from pathlib import Path
from mathutils import Vector

blend, out_blend, frames_dir = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=str(Path(blend).resolve()))
cam = bpy.data.objects.get('CMAI_Static_ThreeQuarter_Camera')
arm = bpy.data.objects['CrimsonSpineBehemoth_Rig']
if cam is None:
    raise RuntimeError('CMAI camera not found')

# Close side/three-quarter framing centered on the Front.L chain.
target = arm.matrix_world @ Vector((0.15, -0.80, -0.15))
cam.location = Vector((0.0, -2.35, 0.12))
cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
cam.data.lens = 85.0
cam.data.clip_start = 0.01
cam.data.clip_end = 100.0
bpy.context.scene.camera = cam
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = 120
bpy.context.scene.render.fps = 24
bpy.context.scene.render.engine = 'BLENDER_WORKBENCH'
bpy.context.scene.render.image_settings.file_format = 'PNG'
out = Path(out_blend).resolve()
fd = Path(frames_dir).resolve(); fd.mkdir(parents=True, exist_ok=True)
bpy.context.scene.render.filepath = str(fd / 'frame_')
bpy.ops.wm.save_as_mainfile(filepath=str(out))
bpy.ops.render.render(animation=True)
print(f'SAVED {out}')
