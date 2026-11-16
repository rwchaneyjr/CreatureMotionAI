"""Draw evaluated Blender leg chains and only evidence-supported reference points."""
import json, math, sys
from pathlib import Path
import cv2, numpy as np

run=Path(sys.argv[1]).resolve()
report=json.loads((run/'image_landmark_report.json').read_text())
ref=cv2.imread(str(run/'reference_frame.png'))
if ref is None:
    cap=cv2.VideoCapture(report['video']); cap.set(cv2.CAP_PROP_POS_FRAMES,int(report.get('reference_frame',report['frame']))-1)
    ok,ref=cap.read(); cap.release()
    if not ok: raise RuntimeError('reference frame unavailable')
ref=cv2.resize(ref,(640,360))
model=cv2.imread(str(run/'model_visual.png'))
if model is None: model=cv2.imread(str(run/'model_aligned.png'))
model=cv2.resize(model,(640,360))
points=report.get('projected_model_landmarks',[])
by={p['name']:p for p in points}
legs=('Front.R','MidFront.R','MidRear.R','Rear.R')
roles=('hip','knee','ankle','foot')
colors=[(80,80,255),(80,210,80),(255,160,60),(220,80,220)]

def xy(p): return np.array(p['xy'],dtype=float)
def angle(a,b,c):
    v=a-b; w=c-b
    den=max(1e-9,np.linalg.norm(v)*np.linalg.norm(w))
    return math.degrees(math.acos(float(np.clip(np.dot(v,w)/den,-1,1))))

model_angles=[]; model_out=model.copy()
for leg,color in zip(legs,colors):
    ps=[by.get(f'{leg} {role}') for role in roles]
    valid=[p for p in ps if p and 0<=p['xy'][0]<640 and 0<=p['xy'][1]<360]
    for a,b in zip(valid,valid[1:]): cv2.line(model_out,tuple(map(int,xy(a))),tuple(map(int,xy(b))),color,2)
    for role,p in zip(roles,ps):
        if p and 0<=p['xy'][0]<640 and 0<=p['xy'][1]<360:
            q=tuple(map(int,xy(p))); cv2.circle(model_out,q,4,color,-1)
    if all(ps):
        a=angle(xy(ps[1]),xy(ps[2]),xy(ps[3]))
        model_angles.append({'leg':leg,'knee_angle_degrees':a,'bend_direction':'IMAGE_ONLY_UNVERIFIED','status':'MODEL_EVALUATED'})
        k=tuple(map(int,xy(ps[1])))
        pass

legacy_path=run.parent.parent/'legacy_video_motion.json'
legacy=json.loads(legacy_path.read_text()) if legacy_path.exists() else {}
row=next((x for x in legacy.get('frames',[]) if int(x.get('frame',-1))==int(report.get('reference_frame',report['frame']))),{})
ref_out=ref.copy(); feet=row.get('leg_candidates',[])
right=[p for p in points if '.R ' in p.get('name','')]
for i,p in enumerate(feet,1):
    x,y=int(p['foot'][0]*640),int(p['foot'][1]*360)
    cv2.circle(ref_out,(x,y),6,(0,200,0),-1); cv2.putText(ref_out,str(i),(x-4,y+4),cv2.FONT_HERSHEY_SIMPLEX,.42,(255,255,255),1)
cv2.imwrite(str(run/'reference_leg_skeleton.png'),ref_out)
cv2.imwrite(str(run/'blender_leg_skeleton.png'),model_out)
overlay=ref.copy()
for i,p in enumerate(feet,1):
    x,y=int(p['foot'][0]*640),int(p['foot'][1]*360); cv2.circle(overlay,(x,y),6,(0,180,0),-1); cv2.putText(overlay,str(i),(x-4,y+4),cv2.FONT_HERSHEY_SIMPLEX,.42,(255,255,255),1)
for li,leg in enumerate(legs):
    pts={p['name'].split()[-1]:p for p in right if p['name'].startswith(leg+' ')}
    ordered=[pts.get(k) for k in roles]; ordered=[p for p in ordered if p and 0<=p['xy'][0]<640 and 0<=p['xy'][1]<360]
    color=colors[li]
    for a,b in zip(ordered,ordered[1:]): cv2.line(overlay,tuple(map(int,xy(a))),tuple(map(int,xy(b))),color,2)
    for p in ordered: cv2.circle(overlay,tuple(map(int,xy(p))),3,color,-1)
cv2.imwrite(str(run/'leg_skeleton_overlay.png'),overlay)
legend=np.full((92,1280,3),25,np.uint8)
cv2.putText(legend,'REFERENCE (left): green numbered feet; hip/knee/ankle UNVERIFIED',(12,22),cv2.FONT_HERSHEY_SIMPLEX,.43,(80,230,80),1)
cv2.putText(legend,'BLENDER (right): colored evaluated chains; reference correspondence UNVERIFIED',(652,22),cv2.FONT_HERSHEY_SIMPLEX,.39,(255,180,40),1)
cv2.putText(legend,'OVERLAY: green=reference foot candidates, colored lines=Blender chains; no correction applied',(12,52),cv2.FONT_HERSHEY_SIMPLEX,.38,(0,220,255),1)
cv2.putText(legend,'Knee angles: '+', '.join(f"{x['leg']} {x['knee_angle_degrees']:.1f} deg" for x in model_angles),(12,78),cv2.FONT_HERSHEY_SIMPLEX,.36,(220,220,220),1)
cv2.imwrite(str(run/'leg_skeleton_overlay_labeled.png'),np.vstack([legend,np.hstack([ref_out,model_out])]))
out={'status':'BLOCKED_NO_VERIFIED_REFERENCE_LEG','reference':{'frame':int(report.get('reference_frame',report['frame'])),'visible_foot_candidates':len(feet),'verified_skeletons':0,'hip_knee_ankle':'UNVERIFIED'},'blender':{'legs':model_angles},'errors_px':[],'corrections':{'status':'NOT_RUN','reason':'No verified reference joints; original Action unchanged'}}
(run/'knee_angle_comparison.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out))
