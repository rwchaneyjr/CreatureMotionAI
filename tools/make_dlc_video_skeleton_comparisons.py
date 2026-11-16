"""Build skeleton videos from the existing DeepLabCut side-video predictions."""
import json,sys
from pathlib import Path
import cv2,numpy as np

root=Path(sys.argv[1]).resolve(); video=Path(sys.argv[2]).resolve(); out=root/'videos_dlc'; out.mkdir(exist_ok=True)
pred=json.loads((root.parent/'selected_video_dlc_frontL_predictions.json').read_text())
pred={int(x['frame']):x for x in pred['frames']}; proj=json.loads((root/'projected_fullbody_skeleton.json').read_text())
approved_path=root.parent/'frontL_selected_video_landmarks.json'
approved=json.loads(approved_path.read_text()) if approved_path.exists() else {}
approved_frames=approved.get('landmarks',{})
cap=cv2.VideoCapture(str(video)); fps=cap.get(cv2.CAP_PROP_FPS) or 24; size=(640,720)
names=('dlc_reference_skeleton.mp4','dlc_blender_skeleton.mp4','dlc_side_by_side_skeleton.mp4')
writers=[cv2.VideoWriter(str(out/n),cv2.VideoWriter_fourcc(*'mp4v'),fps,s) for n,s in zip(names,(size,size,(1280,720)))]
previous=None; rows=[]; start=1
for out_frame in range(1,121):
    ref_frame=start+out_frame-1; cap.set(cv2.CAP_PROP_POS_FRAMES,ref_frame-1); ok,ref=cap.read()
    if not ok: break
    ref=cv2.resize(ref,size); item=pred.get(ref_frame); lm=item.get('landmarks_2d',{}) if item else {}; conf=item.get('confidence',{}) if item else {}
    # Predictions and approved labels are already in the left 640x720 panel.
    # Do not apply the training config's separate y=277 crop offset here.
    points={k:np.array([float(v[0]),float(v[1])]) for k,v in lm.items()}
    confidence=min([float(conf.get(k,0)) for k in ('hip','knee','ankle','foot')] or [0])
    jump=float(max(np.linalg.norm(points[k]-previous[k]) for k in points)) if previous and len(points)==4 else 0
    reliable=confidence>=.75 and (previous is None or jump<80)
    if reliable: previous=points
    # Identity is deliberately not promoted from the JSON field "Front.L".
    # Without a verified physical identity, connected anatomy lines are unsafe.
    connected=False
    approved_error=None
    if str(ref_frame) in approved_frames:
        aa=approved_frames[str(ref_frame)]
        vals=[]
        for k in ('hip','knee','ankle','foot'):
            if k in aa and k in points:
                q=np.array([float(aa[k]['x']),float(aa[k]['y'])])
                vals.append({'landmark':k,'dx':float(points[k][0]-q[0]),'dy':float(points[k][1]-q[1]),'distance_px':float(np.linalg.norm(points[k]-q)),'raw_confidence':float(conf.get(k,0)),'approved_status':aa[k].get('approval')})
        approved_error=vals
    for role,p in points.items():
        q=tuple(map(int,p)); cv2.circle(ref,q,5,(0,190,0) if reliable else (0,220,255),-1)
    cv2.putText(ref,f'REFERENCE DLC POINTS ONLY frame {ref_frame}: {"TRACK-SCREENED / ID UNVERIFIED"}',(10,24),cv2.FONT_HERSHEY_SIMPLEX,.5,(0,220,255),1)
    bl=cv2.imread(str(root/'fullbody_frames'/f'walk_{out_frame:04d}.png')); bl=cv2.resize(bl,size)
    row=proj['frames'][out_frame-1]; cols=[(80,80,255),(80,210,80),(255,160,60),(220,80,220)]
    for li,leg in enumerate(('Front.R','MidFront.R','MidRear.R','Rear.R')):
        pts=row['legs'].get(leg,[]); col=cols[li]
        for a,b in zip(pts,pts[1:]): cv2.line(bl,tuple(map(int,a['xy'])),tuple(map(int,b['xy'])),col,2)
        for p in pts: cv2.circle(bl,tuple(map(int,p['xy'])),4,col,-1)
    cv2.putText(bl,'BLENDER: exact projected rig joints',(10,24),cv2.FONT_HERSHEY_SIMPLEX,.5,(80,80,255),1)
    side=np.hstack([ref,bl]); cv2.putText(side,'DLC leg identity provisional; no bone adjustment',(10,700),cv2.FONT_HERSHEY_SIMPLEX,.5,(0,220,255),1)
    writers[0].write(ref); writers[1].write(bl); writers[2].write(side)
    rows.append({'reference_frame':ref_frame,'confidence':confidence,'max_joint_jump_px':jump,'track_screened':reliable,'physical_leg_identity':'UNVERIFIED','connected_skeleton_drawn':connected,'approved_comparison':approved_error,'bone_adjustment':'NOT_RUN'})
cap.release()
for w in writers:w.release()
report={'status':'DLC_TRACK_REVIEW_ONLY','reference_video':str(video),'reference_start_frame':start,'frames_compared':len(rows),'track_screened_frames':sum(x['track_screened'] for x in rows),'reference_leg_label':'UNVERIFIED (source JSON label not promoted)','blender_leg_projection':'exact evaluated rig chains','knee_angle_comparison':'EXCLUDED until physical identity is verified','bone_adjustment':'NOT_RUN','coordinate_system':'left 640x720 side panel; identity transform','approved_frames_tested':[1,25,49,73,97],'connected_skeleton_policy':'never draw connected lines while identity is unverified','reason':'Raw points are confidence/continuity screened, but no physical leg identity is established; points are shown separately only.','outputs':{n:str(out/n) for n in names},'frames':rows}
(root/'dlc_video_skeleton_report.json').write_text(json.dumps(report,indent=2)); print(json.dumps({k:v for k,v in report.items() if k!='frames'}))
