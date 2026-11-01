"""Generate a separate, reviewable DeepLabCut-style proposal dataset.

This is deliberately conservative: visible silhouette-derived points are marked
as proposals, while hidden-side leg points receive low confidence and are never
presented as accurate labels.
"""
import argparse, json
from pathlib import Path
import cv2, numpy as np, csv

LEGS=['front_left','front_right','midfront_left','midfront_right','midrear_left','midrear_right','rear_left','rear_right']
BODY=['head','neck','shoulder_center','spine_center','hip_center','tail_base','tail_middle','tail_tip']
PARTS=BODY+[f'{leg}_{joint}' for leg in LEGS for joint in ('hip','knee','foot')]

def bbox(img):
    hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV); m=((hsv[:,:,1]>35)&(hsv[:,:,2]>35)).astype('uint8')
    n,lab,stats,cents=cv2.connectedComponentsWithStats(m,8); best=None
    for i in range(1,n):
        x,y,w,h,area=stats[i]
        if area>1000 and (best is None or area>best[4]): best=(x,y,w,h,area)
    return best

def main():
    p=argparse.ArgumentParser(); p.add_argument('--video',required=True); p.add_argument('--output',required=True); p.add_argument('--frames',default='60,120,180'); a=p.parse_args()
    out=Path(a.output); (out/'frames').mkdir(parents=True,exist_ok=True); (out/'overlays').mkdir(parents=True,exist_ok=True)
    indices=[int(x) for x in a.frames.split(',')]; cap=cv2.VideoCapture(a.video); rows=[]; meta=[]
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES,idx); ok,img=cap.read()
        if not ok: continue
        h,w=img.shape[:2]; bb=bbox(img)
        if not bb: continue
        x,y,bw,bh,_=bb; sx=lambda q:x+q*bw; sy=lambda q:y+q*bh
        pts={'head':(sx(.88),sy(.38),1.0),'neck':(sx(.78),sy(.42),.9),'shoulder_center':(sx(.68),sy(.46),.9),'spine_center':(sx(.48),sy(.40),.9),'hip_center':(sx(.28),sy(.47),.85),'tail_base':(sx(.16),sy(.48),.8),'tail_middle':(sx(.07),sy(.52),.65),'tail_tip':(sx(0.0),sy(.55),.55)}
        # Four visible-side proposals; the opposing four are retained with low confidence.
        xs=[.70,.55,.39,.23]; ys=[.70,.74,.76,.73]
        for side,conf,off in [('left',.72,0),('right',.18,7)]:
            for j,leg in enumerate(LEGS[off:off+4] if off else LEGS[:4]):
                q=xs[j]; pts[f'{leg}_hip']=(sx(q),sy(.52),conf); pts[f'{leg}_knee']=(sx(q-.025),sy(.67),conf*.9); pts[f'{leg}_foot']=(sx(q-.05),sy(ys[j]),conf*.85)
        for name,(px,py,conf) in pts.items():
            rows.extend([{'frame':idx,'scorer':'CreatureMotionAI_proposal','bodypart':name,'x':round(px,2),'y':round(py,2),'likelihood':round(conf,3)}])
            color=(0,255,0) if conf>=.6 else (0,165,255)
            cv2.circle(img,(int(px),int(py)),7,color,-1); cv2.putText(img,name,(int(px)+8,int(py)),cv2.FONT_HERSHEY_SIMPLEX,.38,color,1)
        cv2.imwrite(str(out/'frames'/f'frame_{idx:06d}.png'),img)
        cv2.imwrite(str(out/'overlays'/f'frame_{idx:06d}_proposal.png'),img); meta.append({'frame':idx,'bbox':bb,'low_confidence_labels':sum(1 for v in pts.values() if v[2]<.6)})
    cap.release()
    with open(out/'proposals_long.csv','w',newline='',encoding='utf-8') as f:
        wr=csv.DictWriter(f,fieldnames=['frame','scorer','bodypart','x','y','likelihood']); wr.writeheader(); wr.writerows(rows)
    # DLC-compatible single-animal CSV: three header rows (scorer/bodypart/coords).
    with open(out/'proposals_dlc_compatible.csv','w',newline='',encoding='utf-8') as f:
        wr=csv.writer(f); wr.writerow(['scorer']+['CreatureMotionAI_proposal']*(len(PARTS)*3)); wr.writerow(['bodyparts']+sum(([p,p,p] for p in PARTS),[])); wr.writerow(['coords']+sum((['x','y','likelihood'] for _ in PARTS),[]))
        for frame in indices:
            lookup={(r['frame'],r['bodypart']):r for r in rows}; row=[frame]
            for part in PARTS:
                z=lookup.get((frame,part),{'x':'','y':'','likelihood':'低'})
                row += [z.get('x',''),z.get('y',''),z.get('likelihood','')]
            wr.writerow(row)
    report={'video':str(Path(a.video).resolve()),'frames':indices,'landmarks':PARTS,'proposed_rows':len(rows),'manual_review_required':sum(x['low_confidence_labels'] for x in meta),'format':'DLC single-animal CSV-compatible multi-index table plus long review CSV','deeplabcut_installed':False,'note':'Proposals are heuristic silhouette/geometry estimates; no labels are approved as accurate.'}
    (out/'proposal_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8'); print(json.dumps(report,indent=2))
if __name__=='__main__': main()
