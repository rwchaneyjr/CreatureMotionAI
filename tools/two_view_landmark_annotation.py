import cv2, json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]; VIDEO=ROOT/'data/reference/goodspilitbalisk.mp4'; OUT=ROOT/'data/generated/two_view_landmark_annotations.json'; REPORT=ROOT/'data/generated/two_view_geometric_consistency_report.json'
FRAMES=[1,61,121,181,240]; NAMES=['body_center']+[f'landmark_{i}' for i in range(1,12)]; state={'frames':{str(f):{} for f in FRAMES},'video':str(VIDEO)}; current=None; panel=None; clicks=[]
def load_frame(f):
 cap=cv2.VideoCapture(str(VIDEO));cap.set(cv2.CAP_PROP_POS_FRAMES,f-1);ok,img=cap.read();cap.release();return img
def save(): OUT.write_text(json.dumps(state,indent=2))
def mouse(event,x,y,flags,param):
 global clicks
 if event==cv2.EVENT_LBUTTONDOWN and panel is not None:
  side='front' if x<panel.shape[1]//2 else 'side'; px=x if side=='front' else x-panel.shape[1]//2; clicks.append((side,px,y)); redraw()
def redraw():
 img=panel.copy(); cv2.rectangle(img,(0,0),(img.shape[1],48),(255,255,255),-1); cv2.putText(img,'Click FRONT then SIDE for each point | U undo | S save | N next | Q quit',(8,28),cv2.FONT_HERSHEY_SIMPLEX,.55,(0,0,0),1,cv2.LINE_AA)
 for side,x,y in clicks: cv2.circle(img,(x+(0 if side=='front' else panel.shape[1]//2),y),6,(0,0,255),-1)
 cv2.imshow('CMAI two-view annotation',img)
def main():
 global current,panel,clicks,state
 if OUT.exists(): state=json.loads(OUT.read_text())
 for f in FRAMES:
  current=f; panel=load_frame(f); clicks=[]; cv2.namedWindow('CMAI two-view annotation');cv2.setMouseCallback('CMAI two-view annotation',mouse);redraw()
  print(f'Frame {f}: click up to 12 matching pairs, FRONT then SIDE. Press s=save, u=undo, n=next, q=quit. Fewer pairs are allowed for occlusion.')
  while True:
   k=cv2.waitKey(0)&255
   if k==ord('u') and clicks: clicks.pop();redraw()
   elif k==ord('s'):
    for i,name in enumerate(NAMES):
     pts=clicks[i*2:i*2+2]
     if len(pts)==2: state['frames'][str(f)][name]={'front_uv':list(pts[0][1:]),'side_uv':list(pts[1][1:]),'front_conf':1.0,'side_conf':1.0,'visible':True}
    save();print('saved',OUT)
   elif k==ord('n'): break
   elif k==ord('q'): cv2.destroyAllWindows();return
  cv2.destroyAllWindows()
 save();print('Saved',OUT)
main()
