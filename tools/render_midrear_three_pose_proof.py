import bpy,sys
from pathlib import Path
from mathutils import Vector
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
blend,out_dir=args[:2]; out=Path(out_dir); out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(Path(blend).resolve())); s=bpy.context.scene; arm=bpy.data.objects['CrimsonSpineBehemoth_Rig']
cam=bpy.data.objects.get('CMAI_MidRear_Proof_Camera')
if not cam: cam=bpy.data.objects.new('CMAI_MidRear_Proof_Camera',bpy.data.cameras.new('CMAI_MidRear_Proof_Camera')); s.collection.objects.link(cam)
cam.data.type='ORTHO'; cam.data.ortho_scale=.55; cam.location=(-3,-.39,-.10); cam.rotation_euler=(Vector((0,-.39,-.10))-cam.location).to_track_quat('-Z','Y').to_euler(); s.camera=cam
mat=bpy.data.materials.new('CMAI_MidRear_HIGHLIGHT'); mat.diffuse_color=(1,0.05,0.02,1)
for bn in ['Leg_MidRear.L_01','Leg_MidRear.L_02','Leg_MidRear.L_03']:
 p=arm.pose.bones[bn]; o=bpy.data.objects.new('CMAI_MidRear_marker_'+bn,None); o.empty_display_type='SPHERE'; o.empty_display_size=.035; o.color=(1,0.05,0.02,1); o.location=arm.matrix_world@p.head; s.collection.objects.link(o)
s.render.engine='BLENDER_WORKBENCH'; s.render.resolution_x=960; s.render.resolution_y=540; s.render.resolution_percentage=100; s.render.image_settings.file_format='PNG'
for name,fr in [('planted',1),('high_lift',48),('forward_swing',68)]:
 s.frame_set(fr); bpy.context.view_layer.update()
 for bn in ['Leg_MidRear.L_01','Leg_MidRear.L_02','Leg_MidRear.L_03']:
  o=bpy.data.objects['CMAI_MidRear_marker_'+bn]; o.location=arm.matrix_world@arm.pose.bones[bn].head
 s.render.filepath=str(out/f'{name}.png'); bpy.ops.render.render(write_still=True)
print(out)
