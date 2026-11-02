"""Render uncluttered two-view overlays for the eight leg identities."""
import argparse,json
from pathlib import Path
import cv2

LEGS=('Leg_Front.L','Leg_Front.R','Leg_MidFront.L','Leg_MidFront.R','Leg_MidRear.L','Leg_MidRear.R','Leg_Rear.L','Leg_Rear.R')
COLORS=((0,0,255),(0,128,255),(0,255,255),(0,220,0),(255,255,0),(255,80,0),(220,0,220),(255,0,180))
def main():
 p=argparse.ArgumentParser(); p.add_argument('--video',required=True); p.add_argument('--proposals',required=True); p.add_argument('--output',required=True); p.add_argument('--max-frames',type=int,default=24); a=p.parse_args(); data=json.loads(Path(a.proposals).read_text(encoding='utf-8')); cap=cv2.VideoCapture(a.video); out=Path(a.output); out.mkdir(parents=True,exist_ok=True)
 for row in data.get('frames',[])[:a.max_frames]:
  cap.set(cv2.CAP_PROP_POS_FRAMES,int(row['frame'])-1); ok,img=cap.read()
  if not ok: continue
  mid=img.shape[1]//2
  for cam,x0 in (('camera_A',0),('camera_B',mid)):
   for name,item in row.get(cam,{}).get('landmarks',{}).items():
    leg=next((i for i,n in enumerate(LEGS) if name.startswith(n+'_')),None)
    if leg is None: continue
    x=int(float(item['x'])+x0); y=int(float(item['y'])); visible=item.get('visible',False) and item.get('state') not in ('uncertain_rig_gate','uncertain_outside_foreground'); color=COLORS[leg] if visible else (120,120,120)
    cv2.circle(img,(x,y),5,color,-1); cv2.putText(img,str(leg+1),(x+6,y),cv2.FONT_HERSHEY_SIMPLEX,.45,color,1,cv2.LINE_AA)
  cv2.imwrite(str(out/f'frame_{int(row["frame"]):06d}_legs.png'),img)
 cap.release(); print(json.dumps({'output':str(out),'frames':min(a.max_frames,len(data.get('frames',[]))),'note':'Gray points are uncertain; colors identify leg chains.'}))
if __name__=='__main__': main()
