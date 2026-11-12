import cv2, json, numpy as np
vid='data/generated/frontL_leg_visible_5sec.mp4'; proj=json.load(open('data/generated/frontL_leg_visible_marker_projection.json')); cap=cv2.VideoCapture(vid); imgs=[]
colors={'hip':(255,0,255),'knee':(0,255,0),'ankle':(0,165,255),'foot':(0,0,255)}
for f in [1,12,20]:
 cap.set(cv2.CAP_PROP_POS_FRAMES,f-1); ok,im=cap.read()
 if not ok: continue
 h,w=im.shape[:2]
 for kind,x,y in proj[str(f)]:
  px=int(x*w); py=int((1-y)*h); cv2.circle(im,(px,py),12,colors[kind],-1); cv2.putText(im,kind,(px+14,py),0,.7,colors[kind],2)
 cv2.putText(im,f'ACTUAL VIDEO frame {f}',(15,35),0,1,(0,255,255),2); imgs.append(im)
cap.release(); out=np.hstack(imgs); cv2.imwrite('data/generated/frontL_leg_visible_actual_three_frames_marked.png',out); print(out.shape)
