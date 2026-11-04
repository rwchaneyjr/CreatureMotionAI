import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=root/'data/generated/single_camera_verified_leg_landmarks.json'
d=json.loads(p.read_text())
d['leg_identity']='Leg_Rear.L'
d['mapping_verified_by_user']=True
p.write_text(json.dumps(d,indent=2))
report={'status':'BLOCKED_CAMERA_CALIBRATION','annotation_mapping':{'user_label':'rear_left','rig_chain':['Leg_Rear.L_01','Leg_Rear.L_02','Leg_Rear.L_03'],'status':'PASS'},'frames':[1,61,121,181,240],'coordinates_preserved':True,'camera':{'source_panel':'left side-view panel','suspect_two_view_calibration_used':False,'orientation':'APPROXIMATE_SIDE_VIEW_ONLY','scale':'AMBIGUOUS','depth':'UNOBSERVED','status':'INSUFFICIENT_FOR_METRIC_FIT'},'scipy':'AVAILABLE','fit_started':False,'minimum_additional_landmarks':['body center','head center or snout','tail base','one visible ground-contact point','one body-length reference point'],'reason':'The four leg points constrain image motion but do not uniquely determine camera scale, depth, or body-to-rig alignment.'}
(root/'data/generated/single_camera_rear_left_fit_config.json').write_text(json.dumps(report,indent=2))
