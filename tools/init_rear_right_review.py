import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
out=root/'data/generated/dlc_training_suggestions_rear_right.json'
if not out.exists():
    data={'status':'PROVISIONAL_REVIEW_REQUIRED','leg_identity':'Leg_Rear.R','video':str(root/'data/reference/goodspilitbalisk.mp4'),'frames':{str(f):{} for f in [1,61,121,181,240]},'landmark_order':['hip','knee','ankle','foot'],'verified_frames':0,'note':'No automatic labels were invented; every point requires user placement or explicit approval.'}
    out.write_text(json.dumps(data,indent=2),encoding='utf-8')
print(out)
