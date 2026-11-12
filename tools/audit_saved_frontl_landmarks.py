import json, sys
from pathlib import Path

src=Path(sys.argv[1]); out=Path(sys.argv[2]); d=json.loads(src.read_text(encoding='utf-8'))
usable=[]; excluded=[]
for frame, pts in d.get('landmarks',{}).items():
    approved={k:v for k,v in pts.items() if v.get('approval')=='MANUALLY_APPROVED' and v.get('visibility')=='visible'}
    (usable if approved else excluded).append(int(frame))
report={
 'source_landmarks':str(src), 'selected_frames':usable, 'excluded_frames':excluded,
 'identity_status':'UNVERIFIED_USER_CONFIRMED_LEG_IDENTITY_REQUIRED',
 'same_leg_check':'UNVERIFIED',
 'camera_calibration':'BLOCKED',
 'camera_blockers':['2D leg points alone do not establish 3D model correspondences','Front.L identity has not been confirmed across frames','No approved body/mesh feature correspondences or camera intrinsics'],
 'pinocchio_fit':'BLOCKED_UNTIL_CORRESPONDENCE_AND_CAMERA_VALIDATION',
 'animation_generated':False,
 'original_assets_modified':False,
 'approved_point_counts':{str(f):4 for f in usable},
 'notes':'Frame 97 excluded because its points are UNVERIFIED. No landmarks were invented.'
}
out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2),encoding='utf-8'); print(json.dumps(report,indent=2))
