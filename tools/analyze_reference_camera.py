"""Analyze reference camera properties without modifying Blender or creating an Action."""
import argparse, json
from pathlib import Path
import cv2, numpy as np

def main():
    p=argparse.ArgumentParser(); p.add_argument('--video',required=True); p.add_argument('--output',required=True); a=p.parse_args()
    cap=cv2.VideoCapture(a.video)
    if not cap.isOpened(): raise RuntimeError('Cannot open video')
    n=int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0); fps=float(cap.get(cv2.CAP_PROP_FPS) or 0); w=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0); h=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    prev=None; scores=[]; areas=[]
    while True:
        ok,im=cap.read()
        if not ok: break
        gray=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY); _,m=cv2.threshold(gray,150,255,cv2.THRESH_BINARY_INV); areas.append(float(np.count_nonzero(m))/max(m.size,1))
        scores.append(0.0 if prev is None else float(np.mean(cv2.absdiff(gray,prev)))); prev=gray
    cap.release(); arr=np.asarray(scores); area=np.asarray(areas)
    ac=[]
    for lag in range(1,min(max(2,n//2),120)):
        if len(arr)>lag and np.std(arr[:-lag]) and np.std(arr[lag:]): ac.append((lag,float(np.corrcoef(arr[:-lag],arr[lag:])[0,1])))
    cycle=max(ac,key=lambda x:x[1]) if ac else None
    report={'schema_version':1,'status':'REFERENCE_CAMERA_ANALYZED','video':{'path':str(Path(a.video).resolve()),'frames':n,'fps':fps,'duration_seconds':n/fps if fps else None,'resolution':[w,h]},'silhouette':{'area_mean':float(area.mean()) if len(area) else 0,'area_std':float(area.std()) if len(area) else 0,'ground_line':'ESTIMATED_FROM_MASK_NOT_VERIFIED'},'camera':{'stationary_score':float(np.std(scores[1:])) if len(scores)>1 else 0,'projection_preference':'UNRESOLVED','confidence':'LOW','reason':'A single monocular video does not uniquely determine projection or camera distance.'},'timing':{'candidate_cycle_lag_frames':cycle[0] if cycle else None,'cycle_correlation':cycle[1] if cycle else None,'synchronization':'NOT_ESTIMATED_AGAINST_BLENDER'},'uncertainties':['Projection type requires multi-frame model fitting.','Body/ground segmentation is heuristic.','Hidden limbs and 3D depth are unavailable.']}
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2),encoding='utf-8'); print(json.dumps(report))
if __name__=='__main__': main()
