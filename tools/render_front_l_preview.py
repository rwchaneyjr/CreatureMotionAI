import bpy, json, math
from pathlib import Path
from mathutils import Vector

ROOT = Path(r"C:\Users\rober\CreatureMotionAI")
BLEND = ROOT / "data/generated/front_l_ik_visual_step_24f.blend"
OUT = ROOT / "data/generated"
bpy.ops.wm.open_mainfile(filepath=str(BLEND))
s = bpy.context.scene
arm = next(o for o in s.objects if o.type == "ARMATURE")
mesh = next(o for o in s.objects if o.type == "MESH")
if s.camera:
    cam = s.camera
else:
    cam = bpy.data.cameras.new("CMAI_FrontL_Preview_Camera")
    cam_obj = bpy.data.objects.new("CMAI_FrontL_Preview_Camera", cam)
    s.collection.objects.link(cam_obj); s.camera = cam_obj
cam_obj = s.camera
cam = cam_obj.data
cam_obj.location = (0.65, -2.7, 0.35)
cam_obj.rotation_euler = (math.radians(82), 0, math.radians(13))
cam.lens = 58
arm.show_in_front = True
arm.display_type = 'WIRE'
s.render.engine = 'BLENDER_WORKBENCH'
s.render.resolution_x = 800; s.render.resolution_y = 600; s.render.resolution_percentage = 100
s.render.image_settings.file_format = 'PNG'
s.render.fps = 24; s.frame_start = 1; s.frame_end = 24
for f in [1,6,12,18,24]:
    s.frame_set(f); s.render.filepath = str(OUT / f"front_l_fixed_frame{f}.png"); bpy.ops.render.render(write_still=True)
for f in range(1,25):
    s.frame_set(f); s.render.filepath = str(OUT / f"front_l_preview_{f:04d}.png"); bpy.ops.render.render(write_still=True)
scene = {'camera_location': list(cam_obj.location), 'camera_rotation': list(cam_obj.rotation_euler), 'frames': [1,6,12,18,24], 'status':'RENDERED_FIXED_CAMERA'}
(OUT/'front_l_preview_camera.json').write_text(json.dumps(scene, indent=2), encoding='utf-8')
s.render.image_settings.file_format = 'FFMPEG'
s.render.ffmpeg.format = 'MPEG4'
s.render.ffmpeg.codec = 'H264'
s.render.filepath = str(OUT / 'front_l_ik_visual_preview.mp4')
bpy.ops.render.render(animation=True)
