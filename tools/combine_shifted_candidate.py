import cv2, numpy as np, json
from pathlib import Path
root=Path(r'C:\Users\rober\CreatureMotionAI')
cap=cv2.VideoCapture(str(root/'data/reference/goodspilitbalisk.mp4')); cap.set(cv2.CAP_PROP_POS_FRAMES,0); ok,fr=cap.read(); cap.release()
side=fr[:,:640].copy(); cv2.drawMarker(side,(515,336),(255,0,255),cv2.MARKER_CROSS,34,5); cv2.putText(side,'VIDEO original annotation',(15,30),cv2.FONT_HERSHEY_SIMPLEX,.7,(255,0,255),2,cv2.LINE_AA)
model=cv2.imread(str(root/'data/generated/body_length_shifted_model.png')); cv2.putText(model,'3D shifted candidate (UNCONFIRMED)',(15,30),cv2.FONT_HERSHEY_SIMPLEX,.65,(255,0,255),2,cv2.LINE_AA)
meta=json.loads((root/'data/generated/body_length_model_candidates_uv.json').read_text()); p=json.loads((root/'data/generated/body_length_shifted_candidate.json').read_text())['world_xyz']; u=int((meta['y_max']-p[1])/(meta['y_max']-meta['y_min'])*640); v=int((meta['z_max']-p[2])/(meta['z_max']-meta['z_min'])*720); cv2.drawMarker(model,(u,v),(255,0,255),cv2.MARKER_CROSS,34,5)
cv2.imwrite(str(root/'data/generated/body_length_shifted_candidate_comparison.png'),np.hstack([side,model]))
