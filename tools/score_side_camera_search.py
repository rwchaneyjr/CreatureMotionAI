import cv2,json,sys
from pathlib import Path
import numpy as np
video,outdir,outjson=sys.argv[1:]
cap=cv2.VideoCapture(video); cap.set(cv2.CAP_PROP_POS_FRAMES,0); ok,im=cap.read(); cap.release(); ref=im[:,:im.shape[1]//2]
hsv=cv2.cvtColor(ref,cv2.COLOR_BGR2HSV); rm=((hsv[:,:,1]>45)&(hsv[:,:,2]<245)).astype(np.uint8)
scores=[]
for p in sorted(Path(outdir).glob('candidate_*.png')):
 x=cv2.imread(str(p)); x=cv2.resize(x,(ref.shape[1],ref.shape[0])); xm=(np.max(x,axis=2)>18).astype(np.uint8); inter=(rm&xm).sum(); union=(rm|xm).sum(); iou=float(inter/union) if union else 0
 idx=int(p.stem.split('_')[-1]); block,rem=divmod(idx,9)
 scores.append({'file':str(p),'iou':iou,'reference_pixels':int(rm.sum()),'model_pixels':int(xm.sum()),'camera_sign_x':-1 if block==0 else 1,'orthographic_scale':(1.3,1.8,2.3)[rem//3],'target_height_offset':(-0.08,0.0,0.08)[rem%3]})
best=max(scores,key=lambda z:z['iou']); bx=cv2.imread(best['file']); bx=cv2.resize(bx,(ref.shape[1],ref.shape[0])); mask=np.max(bx,axis=2)>18; overlay=ref.copy(); overlay[mask]=((overlay[mask].astype(float)*.55)+(bx[mask].astype(float)*.45)).astype(np.uint8); cv2.imwrite(str(Path(outdir)/'best_overlay.png'),overlay); cv2.imwrite(str(Path(outdir)/'best_side_by_side.png'),np.hstack([ref,bx]))
report={'status':'APPROXIMATE_CAMERA_SEARCH','candidates':scores,'best':best,'metric_calibration':'UNVERIFIED','leg_identity':'UNVERIFIED'}; Path(outjson).write_text(json.dumps(report,indent=2)); print(json.dumps({'best':best,'report':outjson,'overlay':str(Path(outdir)/'best_overlay.png')},indent=2))
