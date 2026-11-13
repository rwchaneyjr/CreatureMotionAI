import bpy,json
scene=bpy.context.scene; arm=bpy.data.objects.get('CrimsonSpineBehemoth_Rig'); scene.frame_set(1); bpy.context.view_layer.update()
legs=['Front.L','Front.R','MidFront.L','MidFront.R','MidRear.L','MidRear.R','Rear.L','Rear.R']
out={'baseline':'data/generated/cmai_exact_standing_baseline_24f.blend','frame':1,'feet':{},'body':{}}
for side in legs:
 n='Leg_'+side+'_03'; p=arm.pose.bones[n]; h=arm.matrix_world@p.head; t=arm.matrix_world@p.tail; out['feet'][side]={'head':list(h),'foot':list(t),'height':t.z}
for n in ['Root','Body_01','Body_02','Body_03']:
 p=arm.pose.bones[n]; h=arm.matrix_world@p.head; t=arm.matrix_world@p.tail; out['body'][n]={'head':list(h),'tail':list(t)}
out['ground_height']=min(v['height'] for v in out['feet'].values()); out['body_height']=max(v['tail'][2] for v in out['body'].values())-out['ground_height']
json.dump(out,open('data/generated/standing_pose_geometry_audit.json','w'),indent=2); print(json.dumps(out))
