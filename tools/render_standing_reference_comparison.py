import bpy, os
from mathutils import Vector
scene=bpy.context.scene; arm=bpy.data.objects.get('CrimsonSpineBehemoth_Rig'); mesh=bpy.data.objects.get('CrimsonSpineBehemoth_Mesh')
scene.frame_set(1); scene.render.engine='BLENDER_WORKBENCH'; scene.display.shading.light='STUDIO'; scene.display.shading.color_type='MATERIAL'; scene.display.shading.show_shadows=True; scene.display.shading.show_cavity=True
cam_data=bpy.data.cameras.new('CMAI_Standing_Reference_Camera_Data'); cam=bpy.data.objects.new('CMAI_Standing_Reference_Camera',cam_data); bpy.context.collection.objects.link(cam)
cam.location=(-3.0,-0.05,-0.18); cam_data.type='ORTHO'; cam_data.ortho_scale=1.7; cam.rotation_euler=(Vector((0,-0.05,-0.10))-cam.location).to_track_quat('-Z','Y').to_euler(); scene.camera=cam
scene.render.resolution_x=640; scene.render.resolution_y=360; scene.render.resolution_percentage=100; scene.render.image_settings.file_format='PNG'; scene.render.filepath=os.path.abspath('data/generated/standing_baseline_reference_frame1.png'); bpy.ops.render.render(write_still=True)
