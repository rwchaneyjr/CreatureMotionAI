import cv2, json, numpy as np
from pathlib import Path
root=Path(r'C:\Users\rober\CreatureMotionAI'); ann=json.loads((root/'data/generated/single_camera_verified_leg_landmarks.json').read_text()); frames=[1,61,121,181,240]; tiles=[]
for f in frames:
    cap=cv2.VideoCapture(str(root/'data/generated/dlc_balisk_side_view.mp4')); cap.set(cv2.CAP_PROP_POS_FRAMES,f-1); ok,img=cap.read(); cap.release()
    if not ok: continue
    for name,col in [('hip',(255,80,80)),('knee',(80,255,80)),('ankle',(80,160,255)),('foot',(255,80,255))]:
        x,y=map(int,ann['frames'][str(f)][name]['uv']); cv2.circle(img,(x,y),9,col,-1); cv2.putText(img,name,(x+8,y-8),cv2.FONT_HERSHEY_SIMPLEX,.45,col,1,cv2.LINE_AA)
    cv2.putText(img,f'DLC imported labels - frame {f}',(10,25),cv2.FONT_HERSHEY_SIMPLEX,.65,(255,255,255),2,cv2.LINE_AA); tiles.append(img)
sheet=np.vstack(tiles); cv2.imwrite(str(root/'data/generated/dlc_imported_labels_contact_sheet.png'),sheet)
