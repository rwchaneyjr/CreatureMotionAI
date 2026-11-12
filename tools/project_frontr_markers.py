import bpy,json
from bpy_extras.object_utils import world_to_camera_view
scene=bpy.context.scene; arm=bpy.data.objects.get('CrimsonSpineBehemoth_Rig'); cam=scene.camera
ns=['Leg_Front.R_01','Leg_Front.R_02','Leg_Front.R_03']; out={}
for f in [1,12,20]:
 scene.frame_set(f); bpy.context.view_layer.update(); pts=[]
 for label,n in [('hip',ns[0]),('knee',ns[1]),('ankle',ns[2])]:
  c=world_to_camera_view(scene,cam,arm.matrix_world@arm.pose.bones[n].head); pts.append((label,c.x,c.y))
 c=world_to_camera_view(scene,cam,arm.matrix_world@arm.pose.bones[ns[2]].tail); pts.append(('foot',c.x,c.y)); out[str(f)]=pts
json.dump(out,open('data/generated/frontR_reference_motion_markers.json','w'),indent=2)
