import bpy,sys
from pathlib import Path
from mathutils import Vector
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
blend,out_dir=args[:2]; out=Path(out_dir); out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(Path(blend).resolve())); s=bpy.context.scene
cam=bpy.data.objects.get('CMAI_MidRear_Closeup')
if not cam: cam=bpy.data.objects.new('CMAI_MidRear_Closeup',bpy.data.cameras.new('CMAI_MidRear_Closeup')); s.collection.objects.link(cam)
cam.data.type='ORTHO'; cam.data.ortho_scale=0.48; cam.location=(-3.0,-0.38,-0.11); cam.rotation_euler=(Vector((0,-0.38,-0.11))-cam.location).to_track_quat('-Z','Y').to_euler(); s.camera=cam
s.render.engine='BLENDER_WORKBENCH'; s.render.resolution_x=960; s.render.resolution_y=540; s.render.resolution_percentage=100; s.render.image_settings.file_format='PNG'; s.render.fps=24
for f in range(1,121): s.frame_set(f); s.render.filepath=str(out/f'frame_{f:04d}.png'); bpy.ops.render.render(write_still=True)
