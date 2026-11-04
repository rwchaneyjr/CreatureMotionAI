import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
land=json.loads((root/'data/generated/single_camera_verified_leg_landmarks.json').read_text())
report={'status':'BLOCKED_CAMERA_UNCERTAIN','annotations':{'leg_identity':land.get('leg_identity'),'frames':list(land.get('frames',{})),'all_four_points':all(len(land['frames'].get(str(f),{}))==4 for f in [1,61,121,181,240])},'rig_candidates':['Leg_Rear.L','Leg_MidRear.L'],'convention':'NOT_VERIFIED','scipy':'AVAILABLE','camera':{'side_panel':'left half of goodspilitbalisk.mp4','calibration':'NOT_VERIFIED','existing_two_view_status':'SUSPECTED_MOTION_INCONSISTENCY'},'action_generated':False,'missing':['verify whether user-selected rear-left corresponds to Leg_Rear.L or Leg_MidRear.L','two or more reliable body reference points for camera scale/orientation','fixed-camera projection calibration']}
(root/'data/generated/single_camera_fit_readiness_report.json').write_text(json.dumps(report,indent=2))
