"""Analyze synchronized split-screen motion in global and local windows."""
import argparse, json
from pathlib import Path
import cv2
import numpy as np

def main():
    p=argparse.ArgumentParser(); p.add_argument('video'); p.add_argument('--output',required=True); p.add_argument('--window',type=int,default=24); a=p.parse_args()
    cap=cv2.VideoCapture(a.video)
    if not cap.isOpened(): raise RuntimeError('Could not open video')
    fps=float(cap.get(cv2.CAP_PROP_FPS) or 24); total=int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0); w=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); h=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)); left=[]; right=[]; prev=None
    while True:
        ok,frame=cap.read()
        if not ok: break
        mid=frame.shape[1]//2; panels=[frame[:,:mid],frame[:,mid:]]; cur=[cv2.resize(cv2.cvtColor(x,cv2.COLOR_BGR2GRAY),(160,90),interpolation=cv2.INTER_AREA) for x in panels]
        if prev is not None:
            left.append(float(np.linalg.norm(cv2.calcOpticalFlowFarneback(prev[0],cur[0],None,.5,2,15,2,5,1.1,0),axis=2).mean()))
            right.append(float(np.linalg.norm(cv2.calcOpticalFlowFarneback(prev[1],cur[1],None,.5,2,15,2,5,1.1,0),axis=2).mean()))
        prev=cur
    cap.release(); windows=[]
    for start in range(0,len(left),a.window):
        x=np.asarray(left[start:start+a.window]); y=np.asarray(right[start:start+a.window]); corr=None
        if len(x)>=3 and x.std()>1e-8 and y.std()>1e-8: corr=float(np.corrcoef(x,y)[0,1])
        windows.append({'start_frame':start+1,'end_frame':min(start+a.window+1,total),'samples':len(x),'correlation':corr,'mean_left_flow':float(x.mean()) if len(x) else 0.0,'mean_right_flow':float(y.mean()) if len(y) else 0.0,'consistent':bool(corr is not None and corr>=0.15)})
    finite=[x['correlation'] for x in windows if x['correlation'] is not None]; report={'input':str(Path(a.video).resolve()),'fps':fps,'frames':total,'resolution':[w,h],'global_correlation':float(np.corrcoef(left,right)[0,1]) if len(left)>2 and np.std(left)>1e-8 and np.std(right)>1e-8 else None,'window_size':a.window,'windows':windows,'consistent_windows':sum(x['consistent'] for x in windows),'total_windows':len(windows),'ready_for_triangulation':bool(w%2==0 and finite and sum(x['consistent'] for x in windows)==len(windows)),'note':'Optical-flow correlation is only a synchronization signal; it does not prove camera geometry or landmark correspondence.'}; Path(a.output).write_text(json.dumps(report,indent=2),encoding='utf-8'); print(json.dumps({'global_correlation':report['global_correlation'],'consistent_windows':report['consistent_windows'],'total_windows':report['total_windows'],'ready_for_triangulation':report['ready_for_triangulation']}))
if __name__=='__main__': main()
