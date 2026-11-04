import cv2, json
from pathlib import Path
import numpy as np

root=Path(r'C:\Users\rober\CreatureMotionAI')
video=root/'data/reference/goodspilitbalisk.mp4'
cal=json.loads((root/'data/generated/single_camera_camera_calibration_annotations.json').read_text())
leg=json.loads((root/'data/generated/single_camera_verified_leg_landmarks.json').read_text())
frames=[1,61,121,181,240]
cap=cv2.VideoCapture(str(video))
panels=[]
for f in frames:
    cap.set(cv2.CAP_PROP_POS_FRAMES,f-1); ok,frame=cap.read()
    if not ok: raise RuntimeError(f'Cannot read frame {f}')
    side=frame[:,:640].copy()
    g=cal['frames'][str(f)]['ground_contact']['uv']; foot=leg['frames'][str(f)]['foot']['uv']
    gx,gy=map(int,g); fx,fy=map(int,foot)
    cv2.drawMarker(side,(gx,gy),(255,0,255),cv2.MARKER_CROSS,32,4)
    cv2.circle(side,(fx,fy),12,(255,255,0),3)
    cv2.putText(side,f'Frame {f}  MAGENTA=ground click  CYAN=Leg_Rear.L foot',(12,28),cv2.FONT_HERSHEY_SIMPLEX,.58,(255,255,255),2,cv2.LINE_AA)
    x0=max(0,min(640-240,gx-120)); y0=max(0,min(720-180,gy-130)); crop=side[y0:y0+180,x0:x0+240]
    crop=cv2.resize(crop,(480,360),interpolation=cv2.INTER_NEAREST)
    full=cv2.resize(side,(480,360),interpolation=cv2.INTER_AREA)
    row=np.hstack([full,crop])
    panels.append(row)
cap.release()
sheet=np.vstack(panels)
out=root/'data/generated/ground_contact_video_review_contact_sheet.png'
cv2.imwrite(str(out),sheet)
(root/'data/generated/ground_contact_video_review.json').write_text(json.dumps({'frames':frames,'video':str(video),'unchanged_annotations':True,'legend':{'magenta':'original calibration ground_contact click','cyan':'original verified Leg_Rear.L foot click'}},indent=2))
candidate=root/'data/generated/ground_contact_closeup.png'
im=cv2.imread(str(candidate))
if im is not None:
    cv2.putText(im,'RED = lowest Leg_Rear.L_03 weighted-foot candidate; not confirmed', (18,32), cv2.FONT_HERSHEY_SIMPLEX, .62, (0,0,255), 2, cv2.LINE_AA)
    cv2.imwrite(str(root/'data/generated/ground_contact_3d_candidates_labeled.png'),im)
