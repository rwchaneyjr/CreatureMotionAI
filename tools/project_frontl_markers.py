import bpy, json
from bpy_extras.object_utils import world_to_camera_view
scene=bpy.context.scene; cam=scene.camera; arm=bpy.data.objects.get('CrimsonSpineBehemoth_Rig')
names=['Leg_Front.L_01','Leg_Front.L_02','Leg_Front.L_03']; out={}
for f in [1,12,20]:
 scene.frame_set(f); bpy.context.view_layer.update(); pts=[]
 for n,kind in [(names[0],'hip'),(names[1],'knee'),(names[2],'ankle')]:
  p=arm.pose.bones[n]; w=arm.matrix_world@p.head; c=world_to_camera_view(scene,cam,w); pts.append((kind,c.x,c.y))
 p=arm.pose.bones[names[2]]; w=arm.matrix_world@p.tail; c=world_to_camera_view(scene,cam,w); pts.append(('foot',c.x,c.y))
 out[str(f)]=pts
json.dump(out,open('data/generated/frontL_leg_visible_marker_projection.json','w'),indent=2); print(out)
