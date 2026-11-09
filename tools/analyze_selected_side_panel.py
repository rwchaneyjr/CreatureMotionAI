"""Create provisional side-panel motion signals without inventing joint labels."""
import argparse, json
from pathlib import Path
import cv2, numpy as np

def main():
    p=argparse.ArgumentParser(); p.add_argument('--video',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    cap=cv2.VideoCapture(str(a.video)); fps=float(cap.get(cv2.CAP_PROP_FPS)); n=int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); rows=[]; prev=None
    for frame in range(1,n+1):
        ok,im=cap.read()
        if not ok: break
        side=im[:,:im.shape[1]//2]; hsv=cv2.cvtColor(side,cv2.COLOR_BGR2HSV)
        mask=((hsv[:,:,1]>35)&(hsv[:,:,2]<250)).astype(np.uint8)*255
        ys,xs=np.where(mask>0)
        if len(xs)>=100:
            bbox=[int(xs.min()),int(ys.min()),int(xs.max()),int(ys.max())]; center=[float(xs.mean()),float(ys.mean())]
        else: bbox=None; center=None
        motion=0.0 if prev is None else float(np.mean(cv2.absdiff(cv2.cvtColor(prev,cv2.COLOR_BGR2GRAY),cv2.cvtColor(side,cv2.COLOR_BGR2GRAY))))
        rows.append({'frame':frame,'panel':'side','body_bbox':bbox,'body_center':center,'motion_signal':motion,'landmarks':{},'confidence':{},'status':'provisional_no_joint_labels'})
        prev=side
    cap.release(); motion=np.asarray([r['motion_signal'] for r in rows]);
    peaks=[]
    for i in range(1,len(rows)-1):
        if motion[i]>=motion[i-1] and motion[i]>=motion[i+1] and motion[i]>max(float(np.percentile(motion,75)),1e-6): peaks.append(rows[i]['frame'])
    result={'status':'PROVISIONAL_SIDE_MOTION_ONLY','source_video':str(a.video.resolve()),'fps':fps,'frames':rows,'candidate_motion_extremes':peaks,'tracking_confidence':'NO_JOINT_TRACKS','note':'Body motion is measured from the selected side panel; no joint positions or verified leg identities were fabricated.'}
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps({'frames':len(rows),'candidate_extremes':peaks,'output':str(a.output)}))
if __name__=='__main__': main()
