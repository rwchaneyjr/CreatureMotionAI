"""Search small frame offsets for split-screen synchronization without lowering thresholds."""
import argparse, json
from pathlib import Path
import cv2, numpy as np

def series(path):
    cap=cv2.VideoCapture(str(path)); left=[]; right=[]; prev=None
    while True:
        ok,f=cap.read()
        if not ok: break
        m=f.shape[1]//2; cur=[cv2.resize(cv2.cvtColor(x,cv2.COLOR_BGR2GRAY),(160,90),interpolation=cv2.INTER_AREA) for x in (f[:,:m],f[:,m:])]
        if prev is not None:
            left.append(float(np.linalg.norm(cv2.calcOpticalFlowFarneback(prev[0],cur[0],None,.5,2,15,2,5,1.1,0),axis=2).mean()))
            right.append(float(np.linalg.norm(cv2.calcOpticalFlowFarneback(prev[1],cur[1],None,.5,2,15,2,5,1.1,0),axis=2).mean()))
        prev=cur
    cap.release(); return np.asarray(left),np.asarray(right),int(cv2.VideoCapture(str(path)).get(cv2.CAP_PROP_FRAME_COUNT) or 0)

def corr(x,y):
    if len(x)<3 or len(y)<3 or x.std()<1e-8 or y.std()<1e-8: return None
    return float(np.corrcoef(x,y)[0,1])

def main():
    p=argparse.ArgumentParser(); p.add_argument('video'); p.add_argument('--output',required=True); p.add_argument('--window',type=int,default=24); p.add_argument('--max-offset',type=int,default=6); a=p.parse_args(); x,y,total=series(a.video); candidates=[]
    for off in range(-a.max_offset,a.max_offset+1):
        windows=[]
        for start in range(0,min(len(x),len(y)),a.window):
            if off>=0: xa=x[start:min(start+a.window,len(x),len(y)-off)]; ya=y[start+off:start+off+len(xa)]
            else: ya=y[start:min(start+a.window,len(y),len(x)+off)]; xa=x[start-off:start-off+len(ya)]
            windows.append(corr(xa,ya))
        valid=[v for v in windows if v is not None]; candidates.append({'offset_frames':off,'mean_window_correlation':float(np.mean(valid)) if valid else None,'min_window_correlation':float(np.min(valid)) if valid else None,'passing_windows':sum(v>=0.15 for v in valid),'total_windows':len(windows),'all_windows_pass':bool(valid and all(v>=0.15 for v in valid)),'windows':windows})
    best=max(candidates,key=lambda z:(z['passing_windows'],z['mean_window_correlation'] or -1,z['min_window_correlation'] or -1)); report={'video':str(Path(a.video).resolve()),'frames':total,'threshold':0.15,'offset_search':[-a.max_offset,a.max_offset],'best_candidate':best,'candidates':candidates,'repairable':bool(best['all_windows_pass']),'conclusion':'repairable_by_fixed_offset' if best['all_windows_pass'] else 'not_reliably_repairable'}; Path(a.output).write_text(json.dumps(report,indent=2),encoding='utf-8'); print(json.dumps({'best_offset':best['offset_frames'],'passing_windows':best['passing_windows'],'total_windows':best['total_windows'],'min':best['min_window_correlation'],'repairable':report['repairable']}))
if __name__=='__main__': main()
