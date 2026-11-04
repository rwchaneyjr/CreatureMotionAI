import json,math
from pathlib import Path
root=Path(__file__).resolve().parents[1];d=json.loads((root/'data/generated/single_camera_camera_calibration_annotations.json').read_text());rows=[]
for f,v in d['frames'].items():
 def dist(a,b): return math.hypot(v[a]['uv'][0]-v[b]['uv'][0],v[a]['uv'][1]-v[b]['uv'][1])
 rows.append({'frame':int(f),'complete':len(v)==5,'body_length_pixels':dist('tail_base','head_snout'),'ground_y':v['ground_contact']['uv'][1],'body_reference_pixels':dist('body_center','body_length_reference')})
report={'status':'UNCERTAIN_CAMERA_MODEL','frames':rows,'body_length_pixel_range':[min(x['body_length_pixels'] for x in rows),max(x['body_length_pixels'] for x in rows)],'ground_y_range':[min(x['ground_y'] for x in rows),max(x['ground_y'] for x in rows)],'reprojection_error':'NOT_COMPUTABLE_WITHOUT_3D_MODEL_POINT_CORRESPONDENCE','camera_ambiguities':['metric depth','intrinsics/lens','true 3D correspondence of body reference point'],'fit_decision':'BLOCKED_UNTIL_MODEL_FEATURE_MAPPING'}
(root/'data/generated/single_camera_calibration_validation.json').write_text(json.dumps(report,indent=2))
