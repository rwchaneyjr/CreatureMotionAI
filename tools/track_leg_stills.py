"""Extract video stills and track lower-contour candidates for eight legs."""
import argparse, json
from pathlib import Path
import cv2, numpy as np

def main():
    p=argparse.ArgumentParser(); p.add_argument('--video',required=True); p.add_argument('--output',required=True); p.add_argument('--frames',required=True); a=p.parse_args(); out=Path(a.output); stills=Path(a.frames); stills.mkdir(parents=True,exist_ok=True)
    out.parent.mkdir(parents=True,exist_ok=True); cap=cv2.VideoCapture(a.video); tracks=[]; index=0
    while True:
        ok,img=cap.read()
        if not ok: break
        cv2.imwrite(str(stills/f'frame_{index:04d}.png'),img)
        hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV); mask=cv2.inRange(hsv,(0,28,20),(179,255,245)); mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((7,7),np.uint8)); points=cv2.findNonZero(mask)
        candidates=[]
        if points is not None:
            x,y,w,h=cv2.boundingRect(points)
            for leg in range(8):
                left=int(x+w*leg/8); right=max(left+1,int(x+w*(leg+1)/8)); crop=mask[int(y+h*.35):y+h,left:right]; local=cv2.findNonZero(crop)
                if local is None: candidates.append({'leg':leg,'foot':None,'confidence':0.0}); continue
                lx,ly,lw,lh=cv2.boundingRect(local); fx=(left+lx+lw/2)/img.shape[1]; fy=(int(y+h*.35)+ly+lh)/img.shape[0]
                candidates.append({'leg':leg,'foot':[fx,fy,0.0],'confidence':min(1.0,lh/max(h*.25,1))})
        tracks.append({'frame':index,'candidates':candidates}); index+=1
    cap.release(); result={'format':'creature_motion_ai.leg_tracks.v1','video':str(Path(a.video).resolve()),'frames':tracks,'notes':'Candidates are image-contour estimates; overlapping legs may share a track and require confidence fallback.'}; out.write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps({'frames':index,'output':str(out),'still_dir':str(stills)}))
if __name__=='__main__': main()
