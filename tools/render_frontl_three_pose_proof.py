import bpy,sys
from pathlib import Path
from mathutils import Vector
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
blend,out_dir=args[:2]; out=Path(out_dir); out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(Path(blend).resolve())); s=bpy.context.scene; arm=bpy.data.objects['CrimsonSpineBehemoth_Rig']
cam=bpy.data.objects.get('CMAI_FrontL_Proof_Camera')
if not cam: cam=bpy.data.objects.new('CMAI_FrontL_Proof_Camera',bpy.data.cameras.new('CMAI_FrontL_Proof_Camera')); s.collection.objects.link(cam)
cam.data.type='ORTHO'; cam.data.ortho_scale=0.55; cam.location=(0,-2.5,0.0); target=arm.matrix_world@Vector((0.15,-0.75,-0.12)); cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler(); s.camera=cam
s.render.engine='BLENDER_WORKBENCH'; s.render.resolution_x=960; s.render.resolution_y=540; s.render.resolution_percentage=100; s.render.image_settings.file_format='PNG'
for name,fr in [('standing',1),('high_lift',41),('forward_swing',81)]:
 s.frame_set(fr); bpy.context.view_layer.update(); s.render.filepath=str(out/f'{name}.png'); bpy.ops.render.render(write_still=True)
print(out)
