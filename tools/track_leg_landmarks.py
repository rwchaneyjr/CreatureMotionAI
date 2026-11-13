"""Track reviewed two-camera leg landmarks through a short reference segment.

Keyframe points are never invented: only visible keyframe points seed optical
flow. Failed tracks become uncertain and are excluded from triangulation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def track_single_view_patches(video, seed_path, output, limit):
    """Track visible textured foot patches with forward/backward LK consistency.

    Seed labels are image-space patch IDs, not inferred anatomical identities.
    Nothing in this mode promotes an observation to manually verified status.
    """
    from scipy.signal import savgol_filter, find_peaks
    seeds=json.loads(seed_path.read_text()); cap=cv2.VideoCapture(str(video))
    fps=float(cap.get(cv2.CAP_PROP_FPS)); frames=[]
    while len(frames)<limit:
        ok,im=cap.read()
        if not ok: break
        frames.append(im)
    cap.release()
    grays=[cv2.cvtColor(im,cv2.COLOR_BGR2GRAY) for im in frames]
    tracked={}; records=[]
    for name,seed in seeds['patches'].items():
        x,y=seed['point']; radius=seed.get('radius',28)
        mask=np.zeros_like(grays[0]); cv2.circle(mask,(x,y),radius,255,-1)
        points=cv2.goodFeaturesToTrack(grays[0],maxCorners=50,qualityLevel=.02,minDistance=3,mask=mask)
        tracked[name]={'features':points,'origin_count':len(points),'position':np.array([x,y],float),'records':[],'lost':False}
    for idx,im in enumerate(frames):
        row={'frame':idx+1,'patches':{}}
        for name,state in tracked.items():
            confidence=1.; fb=0.; jump=0.
            if idx and not state['lost']:
                p=state['features']
                nxt,st,err=cv2.calcOpticalFlowPyrLK(grays[idx-1],grays[idx],p,None,winSize=(31,31),maxLevel=3)
                back,st2,_=cv2.calcOpticalFlowPyrLK(grays[idx],grays[idx-1],nxt,None,winSize=(31,31),maxLevel=3)
                residual=np.linalg.norm(back-p,axis=2).reshape(-1)
                good=(st[:,0]>0)&(st2[:,0]>0)&(residual<1.5)&(err[:,0]<28)
                if good.sum()<5:
                    state['lost']=True
                else:
                    delta=np.median((nxt-p)[good,0],axis=0); jump=float(np.linalg.norm(delta)); fb=float(np.median(residual[good]))
                    state['position']+=delta; state['features']=nxt[good]
                    confidence=float(min(1,good.sum()/max(10,state['origin_count']*.55))*np.exp(-fb))
                    if jump>25: confidence*=.2
            rec={'x':float(state['position'][0]),'y':float(state['position'][1]),'confidence':0. if state['lost'] else confidence,
                 'fb_error_px':fb,'jump_px':jump,'status':'UNVERIFIED_PREDICTION' if not state['lost'] else 'LOST',
                 'identity':seeds['patches'][name].get('identity','UNVERIFIED')}
            row['patches'][name]=rec; state['records'].append(rec)
        records.append(row)
    metrics={}
    for name,state in tracked.items():
        if name=='body': continue
        good=[i for i,r in enumerate(state['records']) if r['confidence']>=.5]
        xy=np.array([[r['x'],r['y']] for r in state['records']]); body=np.array([[r['x'],r['y']] for r in tracked['body']['records']])
        local=xy-body
        smooth=savgol_filter(local,9,2,axis=0)
        image_smooth=savgol_filter(xy,9,2,axis=0)
        valid=np.array([r['confidence']>=.5 for r in state['records']])
        if valid.sum()<12: metrics[name]={'status':'INSUFFICIENT_TRACKING'}; continue
        # In a fixed-camera clip, body bob must not be mistaken for foot lift.
        # Keep image-ground height separate from body-relative forward travel.
        peaks,_=find_peaks(-image_smooth[:,1],prominence=10,distance=18)
        peaks=[int(p) for p in peaks if valid[max(0,p-2):min(len(valid),p+3)].all()]
        periods=np.diff(peaks)
        metrics[name]={'status':'PROVISIONAL_2D','reliable_flow_frames':len(good),'total_frames':len(frames),
            'peak_lift_frames':[p+1 for p in peaks], 'cycle_frames':float(np.median(periods)) if len(periods) else None,
            'horizontal_range_px':float(np.ptp(smooth[valid,0])), 'vertical_range_px':float(np.ptp(image_smooth[valid,1])),
            'maximum_forward_frame':int(np.argmax(np.where(valid,smooth[:,0],-np.inf)))+1,
            'maximum_backward_frame':int(np.argmin(np.where(valid,smooth[:,0],np.inf)))+1,
            'body_relative_foot_xy':smooth.tolist(),'image_foot_xy':image_smooth.tolist(),
            'coordinate_note':'Forward travel is body-relative; lift is image-relative for a fixed camera. No calibrated ground plane or anatomical identity is implied.'}
    payload={'source_video':str(video.resolve()),'fps':fps,'seed_file':str(seed_path.resolve()),'seed_approval':'ASSISTANT_VISUAL_SEEDS_UNVERIFIED',
        'eight_leg_identity':'UNVERIFIED: single-view overlaps and five apparent near-side feet do not establish eight anatomical identities',
        'metrics':metrics,'frames':records}
    output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists(): raise FileExistsError(output)
    output.write_text(json.dumps(payload,indent=2))
    panels=[]; colors=[(255,70,20),(40,180,20),(20,80,255),(180,30,150),(0,170,230),(150,150,0)]
    for idx in [0,12,24,36,48,60,72,84]:
        if idx>=len(frames): continue
        im=frames[idx].copy()
        for j,(name,r) in enumerate(records[idx]['patches'].items()):
            if r['status']=='LOST': continue
            p=(round(r['x']),round(r['y'])); cv2.circle(im,p,8,colors[j],-1)
            cv2.putText(im,name+' ?',(p[0]-20,p[1]-15),0,.65,colors[j],2)
        cv2.putText(im,f'Frame {idx+1} - UNVERIFIED patch tracking',(12,30),0,.7,(0,0,0),2)
        panels.append(cv2.resize(im,(640,360)))
    cv2.imwrite(str(output.with_suffix('.png')),np.vstack([np.hstack(panels[i:i+2]) for i in range(0,len(panels),2)]))
    print(json.dumps({k:{kk:vv for kk,vv in v.items() if kk not in ('body_relative_foot_xy','image_foot_xy')} for k,v in metrics.items()},indent=2))


def read_frames(video: Path, limit: int) -> dict[int, tuple[np.ndarray, np.ndarray]]:
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open {video}")
    out = {}
    for number in range(1, limit + 1):
        ok, frame = cap.read()
        if not ok:
            break
        half = frame.shape[1] // 2
        out[number] = (frame[:, :half], frame[:, half:])
    cap.release()
    return out


def load_seeds(path: Path) -> dict[int, dict[str, dict[str, dict]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    seeds = {}
    for row in data.get("frames", []):
        frame = int(row["frame"])
        if "points" in row:
            cameras = {"camera_A": {}, "camera_B": {}}
            for point in row["points"]:
                for camera in cameras:
                    item = point.get(camera, {})
                    cameras[camera][point["name"]] = {**item, "leg": point.get("leg"), "state": item.get("state", "uncertain")}
            seeds[frame] = cameras
        else:
            seeds[frame] = {camera: row.get(camera, {}).get("landmarks", {}) for camera in ("camera_A", "camera_B")}
    return seeds


def track_one(prev: dict, image_a: np.ndarray, image_b: np.ndarray, image_width: int, image_height: int) -> dict:
    valid = {name: item for name, item in prev.items() if item.get("visible") and item.get("state") not in ("uncertain", "estimated")}
    if not valid:
        return {name: {**item, "state": "uncertain_no_seed", "visible": False} for name, item in prev.items()}
    names = list(valid)
    p0 = np.float32([[valid[name]["x"], valid[name]["y"]] for name in names]).reshape(-1, 1, 2)
    p1, status, errors = cv2.calcOpticalFlowPyrLK(image_a, image_b, p0, None)
    result = {name: {**item, "state": "uncertain_tracking_failed", "visible": False} for name, item in prev.items()}
    for name, point, ok, error in zip(names, p1.reshape(-1, 2), status.reshape(-1), errors.reshape(-1)):
        x, y = map(float, point)
        jump = float(np.linalg.norm(point - p0[names.index(name), 0]))
        good = bool(ok and error < 25.0 and jump < 90.0 and 0 <= x < image_width and 0 <= y < image_height)
        if good:
            result[name] = {**valid[name], "x": x, "y": y, "state": "optical_flow", "visible": True, "confidence": float(valid[name].get("confidence", 0.0)) * 0.92, "flow_error": float(error), "jump_px": jump}
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("seeds", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-frames", type=int, default=24)
    parser.add_argument("--single-view-patches",action="store_true")
    args = parser.parse_args()
    if args.single_view_patches:
        track_single_view_patches(args.video,args.seeds,args.output,args.max_frames)
        return
    images = read_frames(args.video, args.max_frames)
    seeds = load_seeds(args.seeds)
    if not images:
        raise RuntimeError("No video frames available")
    keyframes = sorted(x for x in seeds if x in images)
    if not keyframes:
        raise RuntimeError("No seed frames overlap the available video")
    rows = []
    current = {"camera_A": {}, "camera_B": {}}
    for frame_number in range(1, min(args.max_frames, max(images)) + 1):
        if frame_number in seeds:
            current = seeds[frame_number]
            row_state = "keyframe_seed"
        elif rows:
            previous_images = images[frame_number - 1]
            current = {camera: track_one(current[camera], previous_images[0], images[frame_number][0], images[frame_number][0].shape[1], images[frame_number][0].shape[0]) if camera == "camera_A" else track_one(current[camera], previous_images[1], images[frame_number][1], images[frame_number][1].shape[1], images[frame_number][1].shape[0]) for camera in ("camera_A", "camera_B")}
            row_state = "optical_flow"
        rows.append({"frame": frame_number, "camera_A": {"landmarks": current["camera_A"]}, "camera_B": {"landmarks": current["camera_B"]}, "state": row_state})
    result = {"status": "provisional_identity_tracking", "frames": rows, "keyframes": keyframes, "source_seeds": str(args.seeds.resolve()), "note": "Optical-flow tracks are provisional. Hidden or failed points remain uncertain and must not be triangulated without two-view confirmation."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    visible = sum(sum(int(x.get("visible", False)) for x in row["camera_A"]["landmarks"].values()) + sum(int(x.get("visible", False)) for x in row["camera_B"]["landmarks"].values()) for row in rows)
    print(json.dumps({"output": str(args.output), "frames": len(rows), "keyframes": keyframes, "visible_observations": visible}, indent=2))


if __name__ == "__main__":
    main()
