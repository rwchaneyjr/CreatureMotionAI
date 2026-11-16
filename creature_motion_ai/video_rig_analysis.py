"""Conservative video + rig analysis; never creates an animation Action."""
from __future__ import annotations
import json, math
from pathlib import Path
from typing import Any

def _load(path: Path, default=None):
    if not path or not path.is_file(): return default
    try: return json.loads(path.read_text(encoding='utf-8'))
    except Exception: return default

def _ranges(rows):
    out=[]
    for label in ('RELIABLE','UNCERTAIN','REJECTED'):
        fs=[int(r['frame']) for r in rows if r.get('classification')==label]; groups=[]
        for f in fs:
            if not groups or f != groups[-1][-1]+1: groups.append([f])
            else: groups[-1].append(f)
        out.append({'classification':label,'ranges':[[g[0],g[-1]] for g in groups]})
    return out

def analyze(video: Path, rig_report: Path, output: Path, manual=None, dlc=None):
    import cv2, numpy as np
    output.mkdir(parents=True, exist_ok=True)
    cap=cv2.VideoCapture(str(video))
    if not cap.isOpened(): raise RuntimeError(f'Cannot open reference video: {video}')
    n=int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0); fps=float(cap.get(cv2.CAP_PROP_FPS) or 0)
    w=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0); h=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    duration=n/fps if fps else None
    rig=_load(rig_report,{}) or {}; selected=rig.get('selected_chains',[])
    manual_data=_load(manual,{}) if manual else None
    dlc_data=_load(dlc,{}) if dlc else None
    approved=[]
    if manual_data:
        for key, pts in (manual_data.get('landmarks') or {}).items():
            visible={k:v for k,v in pts.items() if v.get('approval')=='MANUALLY_APPROVED' and v.get('visibility')!='hidden'}
            if visible: approved.append({'frame':int(key),'points':visible,'source':'MANUALLY_APPROVED'})
    dlc_rows=[]
    if dlc_data:
        for row in dlc_data.get('frames',[]):
            conf=row.get('confidence',{}); mean=float(np.mean(list(conf.values()))) if conf else 0.0
            pts=row.get('landmarks_2d',row.get('points',{})); have=all(k in pts for k in ('hip','knee','ankle','foot'))
            lengths=[]
            if have:
                for a,b in (('hip','knee'),('knee','ankle'),('ankle','foot')):
                    lengths.append(float(np.linalg.norm(np.asarray(pts[a])-np.asarray(pts[b]))))
            stable=have and mean>=.6 and (max(lengths)/max(min(lengths),1e-6)<3.5 if lengths else False)
            dlc_rows.append({'frame':int(row.get('frame',0)),'classification':'RELIABLE' if stable else ('UNCERTAIN' if mean>=.35 else 'REJECTED'),'mean_confidence':round(mean,4),'points':pts,'confidence':conf})
    # Conservative silhouette motion signature. It is not joint reconstruction.
    gray_prev=None; motion=[]
    cap.set(cv2.CAP_PROP_POS_FRAMES,0)
    while True:
        ok, frame=cap.read()
        if not ok: break
        gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
        score=0.0 if gray_prev is None else float(np.mean(cv2.absdiff(gray,gray_prev)))
        motion.append(score); gray_prev=gray
    cap.release()
    motion_arr=np.asarray(motion,dtype=float)
    peaks=[]
    if len(motion_arr)>2:
        threshold=float(np.percentile(motion_arr,75)); peaks=[int(i+1) for i in range(1,len(motion_arr)-1) if motion_arr[i]>=threshold and motion_arr[i]>=motion_arr[i-1] and motion_arr[i]>=motion_arr[i+1]]
    # Mark only manually approved landmarks; predictions remain explicitly unverified.
    sheet_frames=[r['frame'] for r in approved[:5]] or [1, max(1,n//4), max(1,n//2), max(1,3*n//4)]
    cap=cv2.VideoCapture(str(video)); tiles=[]
    for f in sheet_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES,max(0,f-1)); ok,im=cap.read()
        if not ok: continue
        im=cv2.resize(im,(640,360)); pts=next((r['points'] for r in approved if r['frame']==f),{})
        sx,sy=640/max(w,1),360/max(h,1)
        colors={'hip':(255,80,40),'knee':(40,220,40),'ankle':(40,180,255),'foot':(255,80,220)}
        for name,p in pts.items():
            x,y=int(float(p['x'])*sx),int(float(p['y'])*sy); cv2.circle(im,(x,y),7,colors.get(name,(255,255,255)),-1); cv2.putText(im,name,(x+8,y),cv2.FONT_HERSHEY_SIMPLEX,.55,(255,255,255),2)
        cv2.putText(im,f'frame {f} | approved 2D only',(12,28),cv2.FONT_HERSHEY_SIMPLEX,.7,(0,255,255),2); tiles.append(im)
    if tiles:
        while len(tiles)<4: tiles.append(np.zeros_like(tiles[0]))
        sheet=np.vstack([np.hstack(tiles[:2]),np.hstack(tiles[2:4])]); cv2.imwrite(str(output/'reference_landmark_review.png'),sheet)
    status='ANALYSIS_COMPLETE_REVIEW_REQUIRED'
    report={'schema_version':1,'status':status,'animation_generated':False,'source_video':str(video),'visual_comparison':{'reference_landmark_review':str(output/'reference_landmark_review.png'),'model_overlay':'NOT_GENERATED_ANALYSIS_ONLY','reason':'A model overlay requires a user-approved camera/anatomy correspondence; no render or Action was created.'},'video':{'frames':n,'fps':fps,'duration_seconds':duration,'width':w,'height':h,'motion_score_mean':float(np.mean(motion_arr)) if len(motion_arr) else 0.0,'motion_peaks_sample':peaks[:40]},'rig':{'source_report':str(rig_report),'armature':rig.get('armature'),'bone_count':rig.get('bone_count'),'candidate_count':rig.get('candidate_count'),'selected_leg_count':rig.get('selected_leg_count'),'mapping_confidence':rig.get('mapping_confidence'),'chains':selected,'confirmed':bool(rig.get('confirmed',False))},'camera_alignment':{'status':'UNVERIFIED_APPROXIMATE','reason':'No independent 3D correspondences or calibrated camera supplied; video is treated as 2D reference only.','metric_3d':'UNAVAILABLE'},'joint_correspondence':{'manual_approved_frames':[r['frame'] for r in approved],'manual_identity':'UNVERIFIED unless user confirms the same physical leg across frames','automatic_predictions':len(dlc_rows),'reliable_predictions':sum(r['classification']=='RELIABLE' for r in dlc_rows),'uncertain_predictions':sum(r['classification']=='UNCERTAIN' for r in dlc_rows),'rejected_predictions':sum(r['classification']=='REJECTED' for r in dlc_rows)},'video_motion':{'tracked_rows':len(dlc_rows),'ranges':_ranges(dlc_rows),'measured_2d_only':bool(dlc_rows),'manual_seed_frames':[r['frame'] for r in approved],'unresolved':['Depth and hidden limbs are not inferred.','Overlapping video legs are not auto-identified.']},'reachability':{'status':'UNVERIFIED','reason':'2D scale/camera alignment is not validated; no 3D target is asserted.','candidate_chains':len(selected)},'animation_plan':{'status':'PROPOSED_NOT_EXECUTED','phases':['plant/support','push/backward body-relative travel','lift/knee bend','forward swing','landing'],'timing_source':'motion signature and reliable tracked rows only','notes':'Waypoints require anatomy/camera review before any Action is created.'},'confidence':{'overall':'LOW_TO_MEDIUM','anatomy':rig.get('mapping_confidence','UNVERIFIED'),'video_tracking':'MEDIUM' if dlc_rows else 'UNVERIFIED','camera':'LOW','3d_fit':'UNVERIFIED'},'unresolved_issues':['Review anatomy candidates and confirm leg identities.','Calibrate or approve approximate side camera.','Validate reachable 3D targets before generating an Action.']}
    (output/'video_rig_analysis.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report
