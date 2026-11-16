import cv2
from pathlib import Path
import numpy as np

root = Path(r'C:\Users\rober\CreatureMotionAI\data\generated\e2e_balisk_test\builder\bending_diagnosis\identity_labels')
bl = cv2.imread(str(root / 'leg_identity_frame_001.png'))
ref = cv2.imread(str(root / 'reference_leg_identity_unverified.png'))
if bl is None or ref is None:
    raise SystemExit('required diagnostic images are missing')

names = ['Front.L','Front.R','MidFront.L','MidFront.R','MidRear.L','MidRear.R','Rear.L','Rear.R']
colors = [(255,70,70),(255,150,50),(70,255,70),(50,220,150),(255,180,50),(255,70,255),(190,70,255),(255,70,190)]
legend = np.zeros((bl.shape[0], 430, 3), dtype=np.uint8)
legend[:] = (32,32,32)
cv2.putText(legend, 'BLENDER LEG MAP', (18,38), cv2.FONT_HERSHEY_SIMPLEX, .9, (255,255,255), 2, cv2.LINE_AA)
cv2.putText(legend, 'Names = confirmed rig chains', (18,72), cv2.FONT_HERSHEY_SIMPLEX, .55, (190,190,190), 1, cv2.LINE_AA)
for i,(n,c) in enumerate(zip(names, colors)):
    y = 120+i*48
    cv2.circle(legend,(28,y-7),10,c,-1)
    cv2.putText(legend, f'{i+1}. {n}', (52,y), cv2.FONT_HERSHEY_SIMPLEX, .7, c, 2, cv2.LINE_AA)
left = np.hstack([bl, legend])
ref = cv2.resize(ref, (left.shape[1], int(ref.shape[0]*left.shape[1]/ref.shape[1])))
top = np.zeros((70,left.shape[1],3),dtype=np.uint8); top[:] = (0,0,0)
cv2.putText(top,'NUMBERED COMPARISON - REFERENCE CANDIDATE LEG IDENTITY UNVERIFIED',(18,45),cv2.FONT_HERSHEY_SIMPLEX,.72,(0,220,255),2,cv2.LINE_AA)
out = np.vstack([top, left, ref])
cv2.imwrite(str(root/'numbered_leg_identity_comparison.png'), out)
print(root/'numbered_leg_identity_comparison.png')
