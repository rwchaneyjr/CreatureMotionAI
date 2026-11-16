"""Export exact evaluated Blender joint projections for a video comparison."""
import json,sys
from pathlib import Path
import bpy
from bpy_extras.object_utils import world_to_camera_view

out=Path(sys.argv[-1]).resolve(); source=Path(sys.argv[-2]).resolve()
bpy.ops.wm.open_mainfile(filepath=str(source)); scene=bpy.context.scene
arm=next(o for o in scene.objects if o.type=='ARMATURE'); cam=scene.camera
w,h=int(scene.render.resolution_x),int(scene.render.resolution_y)
legs=('Front.R','MidFront.R','MidRear.R','Rear.R')
roles=('hip','knee','ankle','foot')
rows=[]
for frame in range(1,121):
    scene.frame_set(frame); bpy.context.view_layer.update(); data={'frame':frame,'legs':{}}
    for leg in legs:
        pts=[]
        for role,suffix in zip(roles,('01','02','03','03')):
            b=arm.pose.bones.get(f'Leg_{leg}_{suffix}')
            if not b: continue
            co=b.tail if role=='foot' else b.head
            uv=world_to_camera_view(scene,cam,arm.matrix_world@co)
            pts.append({'joint':role,'xy':[float(uv.x*w),float((1-uv.y)*h)],'depth':float(uv.z)})
        data['legs'][leg]=pts
    rows.append(data)
(out/'projected_skeleton.json').write_text(json.dumps({'width':w,'height':h,'frames':rows},indent=2))
print(out/'projected_skeleton.json')
