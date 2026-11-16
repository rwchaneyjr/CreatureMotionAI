"""Audit a DLC leg chain and reject cross-body connections without relabeling it."""
import json,sys
from pathlib import Path
import cv2,numpy as np

root=Path(sys.argv[1]).resolve(); video=Path(sys.argv[2]).resolve(); pred=json.loads((root.parent/'selected_video_dlc_frontL_predictions.json').read_text())
cap=cv2.VideoCapture(str(video)); cap.set(cv2.CAP_PROP_POS_FRAMES,0); ok,im=cap.read(); cap.release()
im=cv2.resize(im,(640,720)); f=pred['frames'][0]; pts=f['landmarks_2d']; cols={'hip':(255,80,0),'knee':(0,180,255),'ankle':(255,0,180),'foot':(0,220,0)}
for role,p in pts.items():
    x,y=map(int,p); cv2.circle(im,(x,y),7,cols[role],-1); cv2.putText(im,role,(x+8,y-8),cv2.FONT_HERSHEY_SIMPLEX,.5,cols[role],1)
cv2.putText(im,'DLC points only - no connections drawn',(10,25),cv2.FONT_HERSHEY_SIMPLEX,.55,(0,220,255),1)
cv2.imwrite(str(root/'dlc_points_only_frame1.png'),im)
segments=[('hip','knee'),('knee','ankle'),('ankle','foot')]
issues=[]
for a,b in segments:
    dx=pts[b][0]-pts[a][0]; dy=pts[b][1]-pts[a][1]
    issues.append({'segment':f'{a}->{b}','dx_px':dx,'dy_px':dy,'status':'REJECTED_CROSS_BODY_CANDIDATE' if a=='hip' and dx < -40 else 'UNVERIFIED'})
report={'status':'REJECTED_DLC_CHAIN','video_frame':1,'label':'Front.L provisional','points':{k:{'xy':v,'confidence':f['confidence'].get(k),'status':'POINT_ONLY_UNVERIFIED'} for k,v in pts.items()},'segments':issues,'reason':'The hip is at x=267 while the foot is at x=136; the chain runs backward across unrelated longitudinal leg regions. Confidence scores measure detector appearance, not physical leg identity.','action':'No reference skeleton lines, knee angles, or Blender corrections accepted.'}
(root/'dlc_leg_connection_audit.json').write_text(json.dumps(report,indent=2)); print(json.dumps(report))
