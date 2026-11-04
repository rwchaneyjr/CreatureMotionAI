import cv2, numpy as np
from pathlib import Path
root=Path(r'C:\Users\rober\CreatureMotionAI')
src=cv2.imread(str(root/'data/generated/body_length_candidate_comparison.png'))
if src is None: raise RuntimeError('comparison image missing')
left=src[230:470,360:640].copy(); right=src[230:500,850:1280].copy()
left=cv2.resize(left,(560,480),interpolation=cv2.INTER_CUBIC); right=cv2.resize(right,(860,540),interpolation=cv2.INTER_CUBIC)
cv2.putText(left,'VIDEO frame 1: original click',(12,28),cv2.FONT_HERSHEY_SIMPLEX,.75,(255,0,255),2,cv2.LINE_AA)
labels=['1 Body_02 tail','2 Body_03 head','3 Body_03 tail','4 Head_01 head','5 Body_03 midpoint']
cv2.rectangle(right,(8,8),(430,155),(0,0,0),-1)
for i,t in enumerate(labels): cv2.putText(right,t,(18,35+i*25),cv2.FONT_HERSHEY_SIMPLEX,.55,(255,255,255),1,cv2.LINE_AA)
cv2.putText(right,'MODEL candidate positions',(12,185),cv2.FONT_HERSHEY_SIMPLEX,.72,(255,255,255),2,cv2.LINE_AA)
out=np.zeros((560,1420,3),dtype=np.uint8); out[:480,:560]=left; out[:540,560:1420]=right
cv2.imwrite(str(root/'data/generated/body_length_candidate_numbered_closeup.png'),out)
