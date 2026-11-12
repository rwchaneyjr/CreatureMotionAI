import cv2, os
import numpy as np
ref=r'C:\Users\rober\Downloads\SIDEbalaskWALK.mp4'
cur=r'C:\Users\rober\CreatureMotionAI\data\generated\frontL_reference_direction_5sec.mp4'
out=r'C:\Users\rober\CreatureMotionAI\data\generated\frontL_reference_side_by_side_5sec.mp4'
cr=cv2.VideoCapture(ref); cc=cv2.VideoCapture(cur); wr=None; contact=[]
for i in range(120):
 ok1,a=cr.read(); ok2,b=cc.read()
 if not(ok1 and ok2): break
 a=cv2.resize(a,(640,360)); b=cv2.resize(b,(640,360))
 cv2.putText(a,'REFERENCE - SIDEbalaskWALK',(15,30),0,.75,(0,255,255),2)
 cv2.putText(b,'BLENDER - Front.L only',(15,30),0,.75,(0,255,255),2)
 pair=np.hstack([a,b])
 if i in [0,29,59,89]: contact.append(pair)
 if wr is None: wr=cv2.VideoWriter(out,cv2.VideoWriter_fourcc(*'mp4v'),24,pair.shape[1::-1])
 wr.write(pair)
wr.release(); cr.release(); cc.release()
sheet=np.vstack(contact); cv2.imwrite(r'C:\Users\rober\CreatureMotionAI\data\generated\frontL_reference_four_pose_comparison.png',sheet)
print(out,os.path.getsize(out))
