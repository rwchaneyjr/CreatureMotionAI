import cv2, json, numpy as np
from pathlib import Path
root=Path(r'C:\Users\rober\CreatureMotionAI')
video=root/'data/reference/goodspilitbalisk.mp4'; cap=cv2.VideoCapture(str(video)); cap.set(cv2.CAP_PROP_POS_FRAMES,0); ok,fr=cap.read(); cap.release()
if not ok: raise RuntimeError('video frame unavailable')
side=fr[:,:640].copy(); ann=json.loads((root/'data/generated/single_camera_camera_calibration_annotations.json').read_text())['frames']['1']['body_length_reference']['uv']; x,y=map(int,ann); cv2.drawMarker(side,(x,y),(255,0,255),cv2.MARKER_CROSS,28,4); cv2.putText(side,'VIDEO: BODY-LENGTH REFERENCE click',(12,30),cv2.FONT_HERSHEY_SIMPLEX,.65,(255,0,255),2,cv2.LINE_AA)
model=cv2.imread(str(root/'data/generated/body_length_model_candidates.png'))
meta=json.loads((root/'data/generated/body_length_model_candidates_uv.json').read_text())
for p in meta['points']:
    u=int((meta['y_max']-p['y'])/(meta['y_max']-meta['y_min'])*640); v=int((meta['z_max']-p['z'])/(meta['z_max']-meta['z_min'])*720)
    col=tuple(int(c*255) for c in p['color'][::-1]); cv2.drawMarker(model,(u,v),col,cv2.MARKER_CROSS,24,3); cv2.putText(model,p['label'],(max(2,u-80),max(20,v-10)),cv2.FONT_HERSHEY_SIMPLEX,.42,col,1,cv2.LINE_AA)
out=np.hstack([side,model]); cv2.imwrite(str(root/'data/generated/body_length_candidate_comparison.png'),out)
