"""Create a directly viewable contact sheet from the three comparison MP4s."""
import cv2
from pathlib import Path
import numpy as np

root=Path(__file__).resolve().parents[1]/'data/generated/video_skeleton_compare_20261116/videos_fullbody'
rows=[]
for name in ('reference_skeleton.mp4','blender_skeleton.mp4','side_by_side_skeleton.mp4'):
    cap=cv2.VideoCapture(str(root/name)); frames=[]; total=int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 1)
    for idx in (0,total//2,total-1):
        cap.set(cv2.CAP_PROP_POS_FRAMES,idx); ok,im=cap.read()
        if ok: frames.append(cv2.resize(im,(480,270)))
    cap.release()
    while len(frames)<3: frames.append(np.zeros((270,480,3),np.uint8))
    title=np.full((35,1440,3),25,np.uint8); cv2.putText(title,name,(10,24),cv2.FONT_HERSHEY_SIMPLEX,.65,(255,255,255),1)
    rows.append(np.vstack([title,np.hstack(frames)]))
sheet=np.vstack(rows)
for i,label in enumerate(('start','middle','end')): cv2.putText(sheet,label,(i*480+10,22),cv2.FONT_HERSHEY_SIMPLEX,.5,(0,220,255),1)
out=root.parent/'video_skeleton_contact_sheet_fullbody.png'; cv2.imwrite(str(out),sheet); print(out)
