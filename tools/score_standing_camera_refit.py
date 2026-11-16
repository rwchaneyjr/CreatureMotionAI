"""Fit image framing, rerenderable as camera zoom/shift; keep torso ROI fixed."""
import json,sys
from pathlib import Path
import cv2,numpy as np
from scipy.optimize import minimize

out=Path(sys.argv[1]).resolve(); finish=len(sys.argv)>2
request=json.loads((out/'request.json').read_text()) if (out/'request.json').exists() else {}
def refmask(im):
 hsv=cv2.cvtColor(im,cv2.COLOR_BGR2HSV)
 m=((hsv[:,:,1]>40)&(hsv[:,:,2]>25)).astype('uint8')
 n,lab,stats,_=cv2.connectedComponentsWithStats(m)
 if n<2: raise ValueError('Empty reference silhouette')
 m=(lab==1+np.argmax(stats[1:,4])).astype('uint8')
 return cv2.morphologyEx(m,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
def modelmask(path): return (cv2.imread(str(path),0)>100).astype('uint8')
def metrics(a,b,roi):
 aa=a*roi; bb=b*roi; ay,ax=np.where(aa); by,bx=np.where(bb)
 return dict(body_roi_iou=float((aa&bb).sum()/max(1,(aa|bb).sum())),centroid_error_px=float(np.hypot(ax.mean()-bx.mean(),ay.mean()-by.mean())) if len(bx) else 999,full_iou=float((a&b).sum()/max(1,(a|b).sum())),frame_edge_foreground_pixels=int(b[0,:].sum()+b[-1,:].sum()+b[:,0].sum()+b[:,-1].sum()))
def warp(m,p):
 z,dx,dy=p; return cv2.warpAffine(m,np.float32([[z,0,320*(1-z)+dx],[0,z,180*(1-z)+dy]]),(640,360),flags=cv2.INTER_NEAREST)
def overlay(im,m,roi,title):
 v=im.copy(); tint=np.zeros_like(v); tint[:,:,1]=m*255; v=cv2.addWeighted(v,.7,tint,.3,0)
 contours,_=cv2.findContours(m,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE); cv2.drawContours(v,contours,-1,(0,0,255),1)
 x,y,w,h=cv2.boundingRect(roi); cv2.rectangle(v,(x,y),(x+w,y+h),(255,0,0),1)
 cv2.rectangle(v,(0,0),(640,32),(20,20,20),-1); cv2.putText(v,title,(8,22),0,.5,(255,255,255),1); return v
cfg=json.loads((out/'candidates.json').read_text()); selected=[]; report={}
for view,video in [('side','8leggedSIDEbalaskWALK.mp4'),('front','8leggedBaliskfrontwalk.mp4')]:
 video=request.get(view+'_video',str(Path('C:/Users/rober/Downloads')/video))
 if not video: continue
 cap=cv2.VideoCapture(video); refs=[]
 for f in (26,61,121):
  cap.set(0 if False else cv2.CAP_PROP_POS_FRAMES,f-1); ok,im=cap.read()
  if not ok: raise ValueError('Reference frame unavailable')
  im=cv2.resize(im,(640,360)); refs.append((f,im,refmask(im)))
 cap.release(); f,im,m=refs[0]; cv2.imwrite(str(out/(view+'_reference.png')),im)
 x,y,w,h=cv2.boundingRect(m); roi=np.zeros_like(m); roi[y:y+int(h*.62),x+int(.1*w):x+int(.9*w)]=1
 cv2.imwrite(str(out/(view+'_reference_mask.png')),m*255)
 if not finish:
  candidates=[]
  for c in cfg['profiles']:
   if c['view']!=view: continue
   mask=modelmask(out/c['image']); xx,yy,ww,hh=cv2.boundingRect(mask); z=w/max(ww,1); init=[z,x+w/2-(320+z*(xx+ww/2-320)),y+h/2-(180+z*(yy+hh/2-180))]
   def loss(p):
    q=metrics(m,warp(mask,p),roi); return 1-q['body_roi_iou']+.001*q['centroid_error_px']
   best=minimize(loss,init,method='Nelder-Mead',options={'maxiter':130,'xatol':.001})
   candidates.append(dict(c,zoom=float(best.x[0]),dx=float(best.x[1]),dy=float(best.x[2]),score=float(best.fun)))
  candidates.sort(key=lambda c:c['score']); selected.append(candidates[0]); report[view]=candidates
 else:
  c=next(c for c in json.loads((out/'selected.json').read_text()) if c['view']==view)
  actual_camera=next(p for p in json.loads((out/'camera_profiles.json').read_text())['profiles'] if p['view']==view)
  before=modelmask(out/c['image']); after=modelmask(out/(view+'_after.png'))
  a=metrics(m,before,roi); b=metrics(m,after,roi)
  cv2.imwrite(str(out/(view+'_before_after.png')),np.hstack([overlay(im,before,roi,f'{view} BEFORE IoU {a["body_roi_iou"]:.3f}'),overlay(im,after,roi,f'{view} AFTER IoU {b["body_roi_iou"]:.3f}')]))
  held=[]
  for ff,ii,mm in refs[1:]: held.append(dict(frame=ff,**metrics(mm,after,roi)))
  report[view]=dict(reference_video=video,reference_frame=26,before=a,after=b,held_out=held,camera_profile=str(out/'camera_profiles.json'),camera_view=view,confidence='LOW',landmark_error_px=None,limitations=['Upper 62% of silhouette is a torso proxy, includes head/spikes; not semantic torso segmentation.','Standing limbs differ from walking reference.','No independently verified landmarks for this exact video.','Projection and depth are ambiguous.','Foreground touching an image edge may indicate clipping; these are not approved full-body preview cameras.'],metric_3d_calibration=False)
if not finish:
 (out/'selected.json').write_text(json.dumps(selected,indent=2)); (out/'ranking.json').write_text(json.dumps(report,indent=2))
else: (out/'calibration_report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report if finish else selected,indent=2))
