"""Trace visible-side foreground geometry upward from anonymous foot candidates."""
import json,sys
from pathlib import Path
import cv2,numpy as np

run=Path(sys.argv[1]).resolve(); report=json.loads((run/'image_landmark_report.json').read_text())
cap=cv2.VideoCapture(report['video']); cap.set(cv2.CAP_PROP_POS_FRAMES,int(report.get('reference_frame',36))-1); ok,ref=cap.read(); cap.release()
if not ok: raise RuntimeError('reference frame unavailable')
ref=cv2.resize(ref,(640,360)); gray=cv2.cvtColor(ref,cv2.COLOR_BGR2GRAY)
# White-background segmentation: keep colored creature pixels and exclude the background.
mask=((gray<245)|(np.max(ref,axis=2)-np.min(ref,axis=2)>25)).astype(np.uint8)
mask[:35]=0
legacy=json.loads((run.parent.parent/'legacy_video_motion.json').read_text())
row=next(x for x in legacy['frames'] if int(x['frame'])==int(report.get('reference_frame',36)))
feet=row.get('leg_candidates',[]); colors=[(0,170,255),(80,210,80),(255,150,40),(220,80,220)]
out=ref.copy(); entries=[]
for idx,p in enumerate(feet):
    x0=int(p['foot'][0]*640); y0=int(p['foot'][1]*360); path=[(x0,y0)]; x=x0
    for y in range(y0-8,max(45,y0-125),-4):
        lo=max(0,x-18); hi=min(640,x+19); band=mask[max(0,y-6):min(360,y+7),lo:hi]; xs=np.where(band.max(axis=0)>0)[0]
        if len(xs): x=int(lo+xs[np.argmin(np.abs((lo+xs)-x))]); path.append((x,y))
    path=path[::-1]
    if len(path)<5: continue
    color=colors[idx%len(colors)]
    for a,b in zip(path,path[1:]): cv2.line(out,a,b,color,2)
    pts=[]
    for role,t in zip(('hip','knee','ankle','foot'),(.15,.45,.72,1.0)):
        q=path[min(len(path)-1,int((len(path)-1)*t))]; pts.append({'joint':role,'xy':list(q),'confidence':0.15,'status':'GEOMETRIC_CANDIDATE_UNVERIFIED'})
        cv2.circle(out,q,4,color,-1)
        cv2.putText(out,role[0].upper(),(q[0]+4,q[1]-4),cv2.FONT_HERSHEY_SIMPLEX,.35,color,1)
    entries.append({'candidate':idx+1,'joints':pts,'confidence':0.15,'status':'UNVERIFIED'})
cv2.imwrite(str(run/'reference_leg_bend_candidates.png'),out)
side=cv2.imread(str(run/'blender_leg_skeleton.png')); side=cv2.resize(side,(640,360))
sheet=np.hstack([out,side]); legend=np.full((75,1280,3),25,np.uint8)
cv2.putText(legend,'REFERENCE: geometry traces only; H/K/A/F UNVERIFIED',(12,24),cv2.FONT_HERSHEY_SIMPLEX,.43,(0,210,255),1)
cv2.putText(legend,'BLENDER: evaluated skeleton; no reliable cross-image correspondence',(652,24),cv2.FONT_HERSHEY_SIMPLEX,.39,(255,190,50),1)
cv2.putText(legend,'No knee-angle comparison or bone correction applied',(12,53),cv2.FONT_HERSHEY_SIMPLEX,.4,(220,220,220),1)
cv2.imwrite(str(run/'reference_bend_side_by_side.png'),np.vstack([legend,sheet]))
result={'status':'UNVERIFIED_REFERENCE_GEOMETRY','reference_frame':int(report.get('reference_frame',36)),'candidates':entries,'verified_correspondences':[],'knee_angle_comparison':[],'correction':'NOT_RUN'}
(run/'reference_leg_bend_report.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result))
