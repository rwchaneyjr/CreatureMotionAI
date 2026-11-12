import bpy, os
scene=bpy.context.scene
mesh=bpy.data.objects.get('CrimsonSpineBehemoth_Mesh')
reg=bpy.data.objects.get('CMAI_FrontL_Diagnostic_Region')
if mesh: mesh.hide_render=False
if reg: reg.hide_render=True
cam=bpy.data.objects.get('CMAI_FrontL_Proof_Camera')
cam.location=(-3.2,-0.05,-0.25)
cam.data.ortho_scale=1.65
from mathutils import Vector
cam.rotation_euler=(Vector((0,-0.05,-0.10))-cam.location).to_track_quat('-Z','Y').to_euler()
scene.camera=cam
scene.render.resolution_x=1000; scene.render.resolution_y=700; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.fps=24
frame_dir=os.path.abspath('data/generated/frontL_three_pose_explicit/fullbody_frames')
os.makedirs(frame_dir,exist_ok=True)
for i in range(1,121):
    scene.frame_set(((i-1)%30)+1)
    scene.render.filepath=os.path.join(frame_dir,f'frame_{i:04d}.png')
    bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath('data/generated/frontL_three_pose_explicit_fullbody.blend'))
