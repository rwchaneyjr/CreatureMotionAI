import cv2, os
import numpy as np
ref=r'C:\Users\rober\Downloads\SIDEbalaskWALK.mp4'
cur=r'C:\Users\rober\CreatureMotionAI\data\generated\frontL_three_pose_explicit_reversed_fullbody_5sec.mp4'
out=r'C:\Users\rober\CreatureMotionAI\data\generated\side_reference_comparison_contact_sheet.png'
def samples(path):
 cap=cv2.VideoCapture(path); n=int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); out=[]
 for f in np.linspace(0,n-1,5).astype(int):
  cap.set(cv2.CAP_PROP_POS_FRAMES,int(f)); ok,im=cap.read()
  if ok:
   im=cv2.resize(im,(480,270)); cv2.putText(im,f'frame {f+1}',(12,28),0,.8,(0,255,255),2); out.append(im)
 cap.release(); return out
a=samples(ref); b=samples(cur); rows=[]
for x,y in zip(a,b): rows.append(np.hstack([x,y]))
sheet=np.vstack(rows); cv2.imwrite(out,sheet); print(out)
