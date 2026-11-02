"""Estimate a shared two-view coordinate system for a split-screen creature video."""
import argparse, json
from pathlib import Path
import cv2
import numpy as np

def panel_stats(panel):
    hsv=cv2.cvtColor(panel,cv2.COLOR_BGR2HSV)
    mask=cv2.inRange(hsv,(0,35,20),(179,255,245))
    mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((3,3),np.uint8))
    points=cv2.findNonZero(mask)
    if points is None: return None
    x,y,w,h=cv2.boundingRect(points)
    ys,xs=np.where(mask>0)
    # Ground estimate: lower occupied band, robust to toes and shadows.
    ground=float(np.percentile(ys,92))
    return {'bbox':[int(x),int(y),int(w),int(h)],'center':[float(x+w/2),float(y+h/2)],'height_px':int(h),'ground_row':ground,'foreground_fraction':float(mask.mean()/255.0)}

def main():
    p=argparse.ArgumentParser(); p.add_argument('video',type=Path); p.add_argument('--output',required=True,type=Path); p.add_argument('--frames',type=int,default=24); a=p.parse_args()
    cap=cv2.VideoCapture(str(a.video))
    if not cap.isOpened(): raise RuntimeError(f'Could not open {a.video}')
    width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)); fps=float(cap.get(cv2.CAP_PROP_FPS) or 0); total=int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if width%2: raise ValueError('Video width must be even')
    mid=width//2; rows=[]
    for i in range(min(a.frames,total)):
        ok,frame=cap.read()
        if not ok: break
        rows.append({'frame':i+1,'camera_A_side':panel_stats(frame[:,:mid]),'camera_B_front':panel_stats(frame[:,mid:])})
    cap.release()
    valid=[r for r in rows if r['camera_A_side'] and r['camera_B_front']]
    if not valid: raise RuntimeError('No valid two-view frames')
    side_h=np.array([r['camera_A_side']['height_px'] for r in valid],float); front_h=np.array([r['camera_B_front']['height_px'] for r in valid],float)
    side_g=np.array([r['camera_A_side']['ground_row'] for r in valid],float); front_g=np.array([r['camera_B_front']['ground_row'] for r in valid],float)
    result={'video':str(a.video.resolve()),'resolution':[width,height],'fps':fps,'total_frames':total,'panels':{'width':mid,'height':height,'camera_A':'side','camera_B':'front'},'frames':rows,'normalization':{'median_side_height_px':float(np.median(side_h)),'median_front_height_px':float(np.median(front_h)),'height_scale_front_to_side':float(np.median(side_h)/max(np.median(front_h),1e-6)),'median_side_ground_row':float(np.median(side_g)),'median_front_ground_row':float(np.median(front_g)),'ground_row_delta_px':float(np.median(side_g)-np.median(front_g)),'side_front_height_ratio_median':float(np.median(side_h/front_h))},'status':'provisional_normalization','note':'Foreground-derived estimates; final camera calibration still requires Blender render comparison.'}
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps({'output':str(a.output),'frames':len(rows),'valid_frames':len(valid),'ground_delta_px':result['normalization']['ground_row_delta_px']}))
if __name__=='__main__': main()
