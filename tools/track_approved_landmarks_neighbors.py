"""Track approved side-view landmarks into nearby frames with LK optical flow.

Predictions are written separately and never promoted to manual approval.
"""
import argparse, json
from pathlib import Path
import cv2
import numpy as np

COLORS={"hip":(0,0,255),"knee":(0,165,255),"ankle":(0,200,80),"foot":(255,80,0)}

def frame(cap,n):
    cap.set(cv2.CAP_PROP_POS_FRAMES,n-1); ok,im=cap.read(); return im if ok else None

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('video',type=Path); ap.add_argument('seeds',type=Path); ap.add_argument('out',type=Path); ap.add_argument('--radius',type=int,default=4); args=ap.parse_args()
    seeds=json.loads(args.seeds.read_text(encoding='utf-8')); cap=cv2.VideoCapture(str(args.video))
    fps=cap.get(cv2.CAP_PROP_FPS) or 24; total=int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    approved={int(f):p for f,p in seeds.get('landmarks',{}).items() if any(v.get('approval')=='MANUALLY_APPROVED' for v in p.values())}
    predictions={}; overlays=[]; diagnostics=[]
    for sf,pts in sorted(approved.items()):
        src=frame(cap,sf)
        if src is None: continue
        gray0=cv2.cvtColor(src[:, :src.shape[1]//2],cv2.COLOR_BGR2GRAY)
        for direction in (-1,1):
            for step in range(1,args.radius+1):
                tf=sf+direction*step
                if tf<1 or tf>total: continue
                dst=frame(cap,tf); dst=dst[:, :dst.shape[1]//2]; gray1=cv2.cvtColor(dst,cv2.COLOR_BGR2GRAY)
                pts0=[]; names=[]
                for name,p in pts.items():
                    if p.get('approval')=='MANUALLY_APPROVED' and p.get('visibility')=='visible': pts0.append([[float(p['x']),float(p['y'])]]); names.append(name)
                if not pts0: continue
                p0=np.float32(pts0); p1,st,err=cv2.calcOpticalFlowPyrLK(gray0,gray1,p0,None,winSize=(21,21),maxLevel=3,criteria=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,30,0.01))
                rec={}
                for i,n in enumerate(names):
                    good=bool(st[i][0]); e=float(err[i][0]) if good else None
                    conf=max(0.0,min(1.0,1.0-(e/30.0))) if e is not None else 0.0
                    x,y=(map(float,p1[i][0]) if good else (None,None))
                    rec[n]={'x':x,'y':y,'visibility':'predicted' if good else 'uncertain','approval':'UNVERIFIED','confidence':round(conf,4),'source_frame':sf,'source':'opencv_lk'}
                predictions.setdefault(str(tf),{}).update(rec)
                if direction==1 and step==1:
                    ov=dst.copy();
                    for n,p in rec.items():
                        if p['x'] is not None: cv2.circle(ov,(round(p['x']),round(p['y'])),7,COLORS[n],-1); cv2.putText(ov,n,(round(p['x'])+8,round(p['y'])),0,.5,(255,255,255),1,cv2.LINE_AA)
                    cv2.putText(ov,f'Frame {tf} | PREDICTED | source {sf}',(12,28),0,.7,(0,0,255),2,cv2.LINE_AA); overlays.append((tf,ov))
                diagnostics.append({'source_frame':sf,'target_frame':tf,'direction':direction,'step':step,'mean_confidence':round(float(np.mean([r['confidence'] for r in rec.values()])),4) if rec else 0})
    cap.release(); args.out.parent.mkdir(parents=True,exist_ok=True)
    payload={'status':'PREDICTED_UNVERIFIED','source_video':str(args.video),'panel':'side','seed_file':str(args.seeds),'predicted_landmarks':predictions,'manual_landmarks_unchanged':True,'diagnostics':diagnostics,'frames_processed':sorted(map(int,predictions))}
    args.out.write_text(json.dumps(payload,indent=2),encoding='utf-8')
    if overlays:
        h=max(x.shape[0] for _,x in overlays); w=max(x.shape[1] for _,x in overlays); canvas=np.full((h,w*len(overlays),3),255,np.uint8)
        for i,(n,x) in enumerate(overlays): canvas[:x.shape[0],i*w:i*w+x.shape[1]]=x
        cv2.imwrite(str(args.out.with_suffix('.png')),canvas)
    print(json.dumps({'output':str(args.out),'predicted_frames':payload['frames_processed'],'manual_approval_added':False,'overlay':str(args.out.with_suffix('.png')) if overlays else None},indent=2))
if __name__=='__main__': main()
