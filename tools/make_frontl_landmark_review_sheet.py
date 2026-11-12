import cv2, json, sys
from pathlib import Path
import numpy as np

video=Path(sys.argv[1]); out=Path(sys.argv[2]); frames=[1,25,49,73,97]
cap=cv2.VideoCapture(str(video)); tiles=[]
for f in frames:
    cap.set(cv2.CAP_PROP_POS_FRAMES,f-1); ok,im=cap.read()
    if not ok: continue
    w=im.shape[1]//2; side=im[:, :w].copy()
    cv2.putText(side,f'Frame {f} | SIDE PANEL | Front.L UNVERIFIED',(18,34),cv2.FONT_HERSHEY_SIMPLEX,.72,(0,0,255),2,cv2.LINE_AA)
    cv2.putText(side,'Mark only visible hip, knee, ankle, foot',(18,66),cv2.FONT_HERSHEY_SIMPLEX,.52,(0,0,255),1,cv2.LINE_AA)
    tiles.append(side)
cap.release()
if not tiles: raise RuntimeError('No frames extracted')
h=max(x.shape[0] for x in tiles); w=max(x.shape[1] for x in tiles); blank=np.full((h,w,3),255,np.uint8)
while len(tiles)<5: tiles.append(blank.copy())
sheet=np.hstack(tiles[:5]); cv2.imwrite(str(out),sheet)
Path(str(out)+'.json').write_text(json.dumps({'status':'UNVERIFIED_REVIEW_SHEET','source_video':str(video),'panel':'side','frames':frames,'landmarks':['hip','knee','ankle','foot'],'proposed_points':False,'reason':'No verified Front.L identity or selected-video landmark coordinates exist; no points were guessed.'},indent=2),encoding='utf-8')
print(json.dumps({'output':str(out),'frames':frames,'marked':False}))
