import bpy, os
from mathutils import Vector
scene=bpy.context.scene
mesh=bpy.data.objects.get('CrimsonSpineBehemoth_Mesh'); reg=bpy.data.objects.get('CMAI_FrontL_Diagnostic_Region')
if mesh: mesh.hide_render=False
if reg: reg.hide_render=True
cam=bpy.data.objects.get('CMAI_FrontL_Proof_Camera')
cam.location=(3.2,-0.05,-0.25); cam.data.type='ORTHO'; cam.data.ortho_scale=1.65
cam.rotation_euler=(Vector((0,-0.05,-0.10))-cam.location).to_track_quat('-Z','Y').to_euler(); scene.camera=cam
scene.render.engine='BLENDER_WORKBENCH'
scene.display.shading.light='STUDIO'; scene.display.shading.color_type='MATERIAL'; scene.display.shading.show_shadows=True; scene.display.shading.show_cavity=True; scene.display.shading.show_specular_highlight=True
scene.render.resolution_x=1000; scene.render.resolution_y=700; scene.render.resolution_percentage=100
scene.frame_set(12); scene.render.filepath=os.path.abspath('data/generated/frontL_three_pose_explicit_fullbody_corrected_frame12.png')
bpy.ops.render.render(write_still=True)
