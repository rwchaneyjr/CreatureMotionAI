import cv2, json, math
from pathlib import Path
import numpy as np
root=Path(r'C:\Users\rober\CreatureMotionAI'); video=root/'data/generated/dlc_balisk_side_view.mp4'; anchors=json.loads((root/'data/generated/single_camera_verified_leg_landmarks.json').read_text())
anchor_frames=sorted(int(x) for x in anchors['frames']); selected=sorted(set(anchor_frames+[round(1+i*(240-1)/39) for i in range(40)]))
cap=cv2.VideoCapture(str(video)); imgs={}
for f in range(1,241):
    cap.set(cv2.CAP_PROP_POS_FRAMES,f-1); ok,im=cap.read()
    if ok: imgs[f]=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
cap.release()
parts=['hip','knee','ankle','foot']; suggestions={}
for f in selected:
    if f in anchors['frames']:
        suggestions[str(f)]={p:{**anchors['frames'][str(f)][p],'state':'manual_verified','source':'trusted_anchor'} for p in parts}; continue
    a=min(anchor_frames,key=lambda x:abs(x-f)); pts=np.float32([anchors['frames'][str(a)][p]['uv'] for p in parts]).reshape(-1,1,2); cur=a; step=1 if f>a else -1
    while cur!=f:
        nxt=cur+step; old=imgs[cur]; new=imgs[nxt]; nxtpts,status,err=cv2.calcOpticalFlowPyrLK(old,new,pts,None,winSize=(21,21),maxLevel=3,criteria=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,30,.01));
        if nxtpts is None: break
        pts=nxtpts; cur=nxt
    row={};
    for p,xy in zip(parts,pts.reshape(-1,2)):
        x,y=map(float,xy); conf=0.45 if cur==f else 0.0; row[p]={'uv':[x,y],'visible':bool(conf),'confidence':conf,'state':'provisional_prediction','source':'opencv_optical_flow'}
    suggestions[str(f)]=row
out={'status':'PROVISIONAL_REVIEW_REQUIRED','video':str(video),'leg_identity':'Leg_Rear.L','frames':suggestions,'trusted_anchor_frames':anchor_frames,'selected_frame_count':len(selected),'verified_frame_count':len(anchor_frames),'training_ready':False,'note':'Predictions are never auto-verified.'}
(root/'data/generated/dlc_training_suggestions.json').write_text(json.dumps(out,indent=2))
print(json.dumps({'selected':len(selected),'anchors':anchor_frames,'output':str(root/'data/generated/dlc_training_suggestions.json')}))
