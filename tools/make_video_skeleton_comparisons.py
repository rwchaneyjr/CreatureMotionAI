"""Make reference, Blender, and side-by-side skeleton comparison videos."""
import json,sys
from pathlib import Path
import cv2,numpy as np

root=Path(sys.argv[1]).resolve(); video=Path(sys.argv[2]).resolve(); out=root/'videos_fullbody'; out.mkdir(exist_ok=True)
proj=json.loads((root/'projected_fullbody_skeleton.json').read_text()); legacy=json.loads((root.parent/'sidebar_camera_refit_tests/camera_refit_fd7b8bfdaf/evidence_3035a0e2ae/legacy_video_motion.json').read_text())
legacy={int(x['frame']):x for x in legacy.get('frames',[])}
cap=cv2.VideoCapture(str(video)); fps=cap.get(cv2.CAP_PROP_FPS) or 24; writers=[]; size=(640,720)
names=('reference_skeleton.mp4','blender_skeleton.mp4','side_by_side_skeleton.mp4')
for name,sz in zip(names,(size,size,(1280,720))): writers.append(cv2.VideoWriter(str(out/name),cv2.VideoWriter_fourcc(*'mp4v'),fps,sz))
colors=[(80,80,255),(80,210,80),(255,160,60),(220,80,220)]
rows=[]
def reference_trace(image, feet, idx):
    gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY); mask=((gray<245)|(np.max(image,axis=2)-np.min(image,axis=2)>25)).astype(np.uint8); mask[:45]=0
    traces=[]
    for i,p in enumerate(feet):
        x=int(p['foot'][0]*640); y=int(p['foot'][1]*720); path=[(x,y)]
        for yy in range(y-8,max(45,y-250),-5):
            lo=max(0,x-24); hi=min(640,x+25); band=mask[max(0,yy-7):min(720,yy+8),lo:hi]; xs=np.where(band.max(axis=0)>0)[0]
            if len(xs): x=int(lo+xs[np.argmin(np.abs((lo+xs)-x))]); path.append((x,yy))
        if len(path)>=5:
            path=path[::-1]; col=(0,190,0)
            for a,b in zip(path,path[1:]): cv2.line(image,a,b,col,2)
            for j,t in enumerate((.15,.45,.72,1.0)): cv2.circle(image,path[min(len(path)-1,int((len(path)-1)*t))],4,col,-1)
            traces.append({'candidate':i+1,'points':path,'confidence':0.15})
    return traces
def mask_bbox(image):
    hsv=cv2.cvtColor(image,cv2.COLOR_BGR2HSV)
    m=(hsv[:,:,1]>28).astype(np.uint8)
    ys,xs=np.where(m)
    return (int(xs.min()),int(ys.min()),int(xs.max()),int(ys.max())) if len(xs) else None
def fit_model(image, points, target):
    src=mask_bbox(image)
    if not src or not target: return image,points
    sw=max(1,src[2]-src[0]); sh=max(1,src[3]-src[1]); tw=max(1,target[2]-target[0]); th=max(1,target[3]-target[1])
    scale=min(tw/sw,th/sh); sx=target[0]+(tw-sw*scale)/2-src[0]*scale; sy=target[1]+(th-sh*scale)/2-src[1]*scale
    out=cv2.warpAffine(image,np.float32([[scale,0,sx],[0,scale,sy]]),(640,720),borderValue=(128,128,128))
    mapped=[]
    for row in points:
        q=dict(row); q['xy']=[row['xy'][0]*scale+sx,row['xy'][1]*scale+sy]; mapped.append(q)
    return out,mapped
reference_start_frame=36
cap.set(cv2.CAP_PROP_POS_FRAMES,reference_start_frame-1)
for frame in range(1,121):
    ok,ref=cap.read()
    if not ok: break
    reference_frame=reference_start_frame+frame-1
    ref=cv2.resize(ref,size); ref_traces=reference_trace(ref,legacy.get(reference_frame,{}).get('leg_candidates',[]),reference_frame)
    bl=cv2.imread(str(root/'fullbody_frames'/f'walk_{frame:04d}.png'))
    if bl is None: bl=np.zeros(size[::-1]+(3,),np.uint8)
    bl=cv2.resize(bl,size); row=proj['frames'][frame-1]
    ref_box=mask_bbox(ref); raw_points=[p for leg in row['legs'].values() for p in leg]
    bl, mapped_points=fit_model(bl,raw_points,ref_box)
    for li,leg in enumerate(('Front.R','MidFront.R','MidRear.R','Rear.R')):
        pts=[p for p in mapped_points if p.get('joint') in ('hip','knee','ankle','foot')]
        # Preserve chain order by selecting the points belonging to this leg.
        raw=row['legs'].get(leg,[]); pts=[]
        for p in raw:
            pts.append(next((q for q in mapped_points if q is not p and q.get('joint')==p.get('joint') and q['xy'][0]==p['xy'][0]*1),p))
        # The identity above is intentionally conservative; remap by original order.
        start=sum(len(row['legs'].get(x,[])) for x in ('Front.R','MidFront.R','MidRear.R','Rear.R')[:li])
        pts=mapped_points[start:start+len(raw)]
        col=colors[li]
        for a,b in zip(pts,pts[1:]): cv2.line(bl,tuple(map(int,a['xy'])),tuple(map(int,b['xy'])),col,2)
        for p in pts: cv2.circle(bl,tuple(map(int,p['xy'])),4,col,-1)
    cv2.putText(ref,'REFERENCE: candidate traces UNVERIFIED',(10,24),cv2.FONT_HERSHEY_SIMPLEX,.5,(0,190,0),1)
    cv2.putText(bl,'BLENDER: exact projected .R rig joints',(10,24),cv2.FONT_HERSHEY_SIMPLEX,.5,(80,80,255),1)
    side=np.hstack([ref,bl]); cv2.putText(side,'No yellow correspondence lines: reference leg identity UNVERIFIED',(10,700),cv2.FONT_HERSHEY_SIMPLEX,.5,(0,220,255),1)
    writers[0].write(ref); writers[1].write(bl); writers[2].write(side)
    rows.append({'frame':frame,'reference_candidate_traces':len(ref_traces),'verified_reference_legs':0,'numeric_comparison':'EXCLUDED'})
cap.release()
for w in writers:w.release()
report={'status':'TRACKING_CORRESPONDENCE_UNVERIFIED','reference_video':str(video),'blender_source':'balisk_camera_baseline_walk.blend','frames_compared':len(rows),'reference_start_frame':reference_start_frame,'phase_alignment':'NOT_ACCEPTED','reference_skeleton':'candidate contour traces only','blender_skeleton':'exact projected evaluated rig joints','verified_leg_correspondences':0,'knee_angle_comparisons':[],'bone_adjustment':'NOT_RUN','reason':'Reference hip/knee/ankle identities are not verified; no safe bone target exists.','frames':rows,'outputs':{n:str(out/n) for n in names}}
(root/'video_skeleton_comparison_report.json').write_text(json.dumps(report,indent=2)); print(json.dumps(report))
