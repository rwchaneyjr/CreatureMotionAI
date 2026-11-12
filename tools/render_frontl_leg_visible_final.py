import bpy, os
from mathutils import Vector
scene=bpy.context.scene; mesh=bpy.data.objects.get('CrimsonSpineBehemoth_Mesh'); reg=bpy.data.objects.get('CMAI_FrontL_Diagnostic_Region')
if mesh: mesh.hide_render=False; mesh.color=(0.32,0.32,0.32,1)
if reg:
 reg.hide_render=False; reg.color=(1.0,0.05,0.01,1)
 for m in reg.data.materials:
  m.diffuse_color=(1.0,0.02,0.005,1); m.metallic=0.0; m.roughness=0.35
cam=bpy.data.objects.get('CMAI_FrontL_Proof_Camera'); cam.location=(-2.4,-1.85,-0.16); cam.data.type='ORTHO'; cam.data.ortho_scale=1.25; cam.rotation_euler=(Vector((0,-0.78,-0.11))-cam.location).to_track_quat('-Z','Y').to_euler(); scene.camera=cam
scene.render.engine='BLENDER_WORKBENCH'; scene.display.shading.light='STUDIO'; scene.display.shading.color_type='OBJECT'; scene.display.shading.show_shadows=True; scene.display.shading.show_cavity=True; scene.display.shading.show_specular_highlight=True
scene.render.resolution_x=1000; scene.render.resolution_y=700; scene.render.resolution_percentage=100; scene.render.image_settings.file_format='PNG'; scene.render.fps=24
d=os.path.abspath('data/generated/frontL_leg_visible_frames'); os.makedirs(d,exist_ok=True)
for i in range(1,121):
 scene.frame_set(((i-1)%30)+1); scene.render.filepath=os.path.join(d,f'frame_{i:04d}.png'); bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath('data/generated/frontL_leg_visible.blend'))
