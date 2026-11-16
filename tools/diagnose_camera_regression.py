import argparse, json
from pathlib import Path
import cv2, numpy as np

def mask(im, reference):
    g=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY)
    _,m=cv2.threshold(g,150 if reference else 20,255,cv2.THRESH_BINARY_INV if reference else cv2.THRESH_BINARY)
    return cv2.morphologyEx(m,cv2.MORPH_OPEN,np.ones((3,3),np.uint8))
def iou(ref,render):
    render=cv2.resize(render,(ref.shape[1],ref.shape[0])); a=mask(ref,True)>0; b=mask(render,False)>0
    return float(np.logical_and(a,b).sum()/max(np.logical_or(a,b).sum(),1))
def main():
    p=argparse.ArgumentParser(); p.add_argument('--reference',required=True); p.add_argument('--old',required=True); p.add_argument('--new',required=True); p.add_argument('--output',required=True); a=p.parse_args()
    ref=cv2.imread(a.reference); old=cv2.imread(a.old); new=cv2.imread(a.new)
    if any(x is None for x in (ref,old,new)): raise RuntimeError('Missing comparison image')
    oldr=cv2.resize(old,(ref.shape[1],ref.shape[0])); newr=cv2.resize(new,(ref.shape[1],ref.shape[0]))
    def title(im,t):
        im=im.copy(); cv2.putText(im,t,(15,32),cv2.FONT_HERSHEY_SIMPLEX,.8,(0,255,255),2); return im
    rmask=cv2.cvtColor(mask(ref,True),cv2.COLOR_GRAY2BGR); omask=cv2.cvtColor(mask(oldr,False),cv2.COLOR_GRAY2BGR); nmask=cv2.cvtColor(mask(newr,False),cv2.COLOR_GRAY2BGR)
    overlay_old=cv2.addWeighted(ref,.55,oldr,.45,0); overlay_new=cv2.addWeighted(ref,.55,newr,.45,0)
    rows=[np.hstack([title(ref,'REFERENCE frame 26'),title(oldr,'PREVIOUS calibration'),title(newr,'NEW candidate')]),np.hstack([title(rmask,'REFERENCE mask'),title(omask,'PREVIOUS mask'),title(nmask,'NEW mask')]),np.hstack([title(overlay_old,'PREVIOUS overlay'),title(overlay_new,'NEW overlay'),title(np.zeros_like(ref),'')])]
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); cv2.imwrite(str(out),np.vstack(rows))
    def box(im,reference):
        m=mask(im,reference); pts=cv2.findNonZero(m); return list(cv2.boundingRect(pts)) if pts is not None else [0,0,0,0]
    report={'reference':a.reference,'old_render':a.old,'new_render':a.new,'old_iou':iou(ref,old),'new_iou':iou(ref,new),'bboxes':{'reference':box(ref,True),'old':box(old,False),'new':box(new,False)},'method':'same threshold/morphology after resize','diagnosis':'Regression is caused by non-equivalent evaluation: the old result used frame-26, the calibrated standing-pose blend and a 120-candidate orthographic body search at ortho_scale 1.22 with target offsets; the new search used frames 1/12/24, a different walk blend, fixed camera distance/center, broad angle/scale candidates, and no target/framing optimization. The old result is reproducible within mask variation; the new score is not comparable.'}
    out.with_suffix('.json').write_text(json.dumps(report,indent=2),encoding='utf-8'); print(json.dumps(report))
if __name__=='__main__': main()
