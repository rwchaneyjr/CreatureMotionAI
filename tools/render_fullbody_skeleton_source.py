"""Render full-body baseline frames from the saved side camera and export joints."""
import json,sys
from pathlib import Path
import bpy
from bpy_extras.object_utils import world_to_camera_view

root=Path(sys.argv[-1]).resolve(); source=Path(sys.argv[-2]).resolve()
profiles=json.loads((root.parent/'sidebar_camera_refit_tests/camera_refit_fd7b8bfdaf/camera_profiles.json').read_text())['profiles']
prof=profiles[0]
bpy.ops.wm.open_mainfile(filepath=str(source)); scene=bpy.context.scene
arm=next(o for o in scene.objects if o.type=='ARMATURE')
data=bpy.data.cameras.new('CMAI_FullBody_Side'); cam=bpy.data.objects.new('CMAI_FullBody_Side',data); scene.collection.objects.link(cam)
cam.location=prof['location']; cam.rotation_euler=prof['rotation_euler']; data.type=prof['projection']; data.lens=prof['focal_length']; data.ortho_scale=prof['ortho_scale']; data.shift_x=prof['shift_x']; data.shift_y=prof['shift_y']; scene.camera=cam
scene.render.resolution_x=640; scene.render.resolution_y=720; scene.render.resolution_percentage=100; scene.render.image_settings.file_format='PNG'; scene.render.engine='BLENDER_WORKBENCH'; scene.display.shading.light='STUDIO'; scene.display.shading.color_type='MATERIAL'; scene.display.shading.show_shadows=False; scene.display.shading.show_cavity=False
frames=root/'fullbody_frames'; frames.mkdir(exist_ok=True); rows=[]; legs=('Front.R','MidFront.R','MidRear.R','Rear.R'); roles=('hip','knee','ankle','foot')
for frame in range(1,121):
    scene.frame_set(frame); bpy.context.view_layer.update(); scene.render.filepath=str(frames/f'walk_{frame:04d}.png'); bpy.ops.render.render(write_still=True); d={'frame':frame,'legs':{}}
    for leg in legs:
        d['legs'][leg]=[]
        for role,suf in zip(roles,('01','02','03','03')):
            b=arm.pose.bones.get(f'Leg_{leg}_{suf}')
            if b:
                co=b.tail if role=='foot' else b.head; uv=world_to_camera_view(scene,cam,arm.matrix_world@co); d['legs'][leg].append({'joint':role,'xy':[float(uv.x*640),float((1-uv.y)*720)]})
    rows.append(d)
(root/'projected_fullbody_skeleton.json').write_text(json.dumps({'width':640,'height':720,'frames':rows},indent=2)); print(root/'fullbody_frames')
