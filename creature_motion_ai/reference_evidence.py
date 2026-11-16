"""Timestamped image measurements, without assigning anonymous contours to legs.

Runs in the existing OpenCV environment. A periodic silhouette is supporting
evidence, not proof of any individual leg's cycle or a cross-view correspondence.
"""
import hashlib
import json
from pathlib import Path


def file_hash(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def select_reference_pose(measurements, video):
    """Choose an intact, stable segmented pose; never infer a named leg identity."""
    import math
    if measurements.get('source_sha256') != file_hash(video):
        raise ValueError('Saved measurements belong to a different video. Run Measure Side Video again.')
    width, height = measurements['resolution']
    diagonal = math.hypot(width, height)
    frames = measurements['frames']
    candidates = []
    for index in range(1, len(frames)-1):
        previous, row, following = frames[index-1:index+2]
        neighbors = (previous, row, following)
        if any(r.get('status') != 'MEASURED_IMAGE_ONLY' or r.get('clipped', True) for r in neighbors):
            continue
        if following['frame']-previous['frame'] != 2:
            continue
        area = row.get('area_pixels', 0)
        if area <= 0 or len(row.get('lower_contour', [])) < 12:
            continue
        center = row['silhouette_centroid_xy']
        drift = max(math.dist(center, r['silhouette_centroid_xy'])/diagonal for r in neighbors)
        area_change = max(abs(r['area_pixels']/area-1) for r in neighbors)
        if drift > .02 or area_change > .1:
            continue
        x,y,w,h = row['bbox_xywh']
        margin = min(x,y,width-x-w,height-y-h)/min(width,height)
        quality = min(1,margin/.03)-10*drift-2*area_change
        candidates.append({'frame':row['frame'],'timestamp_seconds':row['timestamp_seconds'],
                           'quality':quality,'centroid_neighbor_drift_fraction':drift,
                           'neighbor_area_change_fraction':area_change,'image_margin_fraction':margin})
    if not candidates:
        raise ValueError('No intact, locally stable measured side silhouette. Best animation retained.')
    best = max(candidates,key=lambda row:row['quality'])
    return dict(best, eligible_frames=len(candidates), mode='AUTOMATIC',
                evidence='Measured silhouette with consecutive-frame consistency; no verified joints',
                leg_identity='UNVERIFIED', timing_synchronization='UNVERIFIED')


def foreground_mask(image):
    """Reuse the calibrated studio-video mask; reject empty/degenerate results."""
    import cv2
    import numpy as np
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask = ((hsv[:, :, 1] > 40) & (hsv[:, :, 2] > 25)).astype('uint8')
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    if count < 2:
        return None
    mask = (labels == 1 + np.argmax(stats[1:, 4])).astype('uint8')
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    if not .005 < float(mask.mean()) < .85:
        return None
    return mask


def estimate_recurrence(descriptors, fps):
    import numpy as np
    from scipy.signal import find_peaks
    data = np.asarray(descriptors, dtype=float)
    if len(data) < 24 or fps <= 0:
        return {'status': 'UNVERIFIED', 'reason': 'Too few contiguous samples.'}
    data -= data.mean(axis=0)
    first = max(3, int(.4 * fps))
    last = min(len(data) // 2, int(5 * fps))
    def similarity(a, b):
        denominator = np.linalg.norm(a) * np.linalg.norm(b)
        return float(np.sum(a*b) / denominator) if denominator > 1e-12 else 0.0
    curve = [{'lag_frames': lag, 'correlation': similarity(data[:-lag], data[lag:])}
             for lag in range(first, last + 1)]
    peaks, properties = find_peaks([r['correlation'] for r in curve], prominence=.05)
    candidates = sorted([dict(curve[i], prominence=float(p))
                         for i, p in zip(peaks, properties['prominences'])],
                        key=lambda row: row['correlation'], reverse=True)
    if not candidates:
        return {'status': 'UNVERIFIED', 'curve': curve, 'reason': 'No non-adjacent recurrence peak.'}
    best = candidates[0]; lag = best['lag_frames']; half = len(data)//2
    halves = [similarity(part[:-lag], part[lag:]) if len(part)>lag+5 else None
              for part in (data[:half], data[half:])]
    supported = best['correlation'] >= .65 and all(c is not None and c >= .5 for c in halves)
    return {'status': 'SUPPORTED_VISUAL_RECURRENCE' if supported else 'UNVERIFIED',
            'candidate_period_frames': lag, 'candidate_period_seconds': lag/fps,
            'correlation': best['correlation'], 'half_clip_correlations': halves,
            'alternatives': candidates[:5], 'curve': curve,
            'individual_leg_cycle_verified': False, 'blender_phase_offset_seconds': None,
            'front_timing_used': False,
            'reason': 'Anonymous lower-silhouette recurrence; harmonics and leg phase remain ambiguous.'}


def analyze_manifest(manifest_path, output):
    import cv2
    import numpy as np
    from .video_analysis import analyze_video
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8-sig'))
    video = Path(manifest['inputs']['side_video']).resolve()
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    # Retain the existing analysis output, explicitly provisional.
    coarse = analyze_video(video)
    (output/'legacy_video_motion.json').write_text(json.dumps(coarse))
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened(): raise ValueError('Cannot read side video')
    fps = float(cap.get(cv2.CAP_PROP_FPS)); width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if fps <= 0: raise ValueError('Video frame rate unavailable')
    rows, descriptors, images = [], [], []
    while True:
        ok, image = cap.read()
        if not ok: break
        frame = len(rows)+1; timestamp = float(cap.get(cv2.CAP_PROP_POS_MSEC))/1000
        mask = foreground_mask(image)
        row = {'frame': frame, 'timestamp_seconds': timestamp, 'identity': 'UNVERIFIED',
               'measurement_type': 'anonymous_silhouette', 'verified_joint_positions': {}}
        if mask is None:
            row['status'] = 'UNVERIFIED_SEGMENTATION'; descriptors.append(None)
        else:
            x,y,w,h = cv2.boundingRect(mask); ys,xs = np.where(mask)
            lower = mask[y+int(.62*h):y+h, x:x+w]
            descriptor = cv2.resize(lower.astype('float32'), (48,16), interpolation=cv2.INTER_AREA).ravel()
            descriptors.append(descriptor)
            row.update(status='MEASURED_IMAGE_ONLY', bbox_xywh=[x,y,w,h],
                       silhouette_centroid_xy=[float(xs.mean()),float(ys.mean())],
                       lower_contour_bottom_y=int(ys.max()), area_pixels=int(mask.sum()),
                       clipped=bool(mask[0].any() or mask[-1].any() or mask[:,0].any() or mask[:,-1].any()))
            row['lower_contour'] = []
            for xx in np.linspace(x,x+w-1,24).astype(int):
                yy=np.flatnonzero(mask[:,xx])
                if len(yy): row['lower_contour'].append([int(xx),int(yy.max())])
        rows.append(row)
        if frame in (1,26,61,121,201):
            display=cv2.resize(image,(640,360))
            if mask is not None:
                contours,_=cv2.findContours(cv2.resize(mask,(640,360)),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
                cv2.drawContours(display,contours,-1,(0,220,255),1)
            cv2.putText(display,f'Frame {frame}: silhouette only; legs UNVERIFIED',(8,24),0,.5,(0,0,0),2)
            images.append(display)
    cap.release()
    timestamps=[r['timestamp_seconds'] for r in rows]
    valid_pts=all(b>a for a,b in zip(timestamps,timestamps[1:]))
    if not valid_pts:
        for row in rows: row['timestamp_seconds']=(row['frame']-1)/fps
    if any(d is None for d in descriptors):
        timing={'status':'UNVERIFIED','reason':'Segmentation gaps; no interpolated cycle measurement.'}
    else:
        timing=estimate_recurrence(descriptors,fps)
    timing.update(fps=fps,frames=len(rows),timestamp_source='decoder_POS_MSEC' if valid_pts else 'nominal_fps_fallback',
                  source_video=str(video),source_sha256=file_hash(video),timing_source='side')
    measured=[r for r in rows if r['status']=='MEASURED_IMAGE_ONLY']
    extrema={}
    for label,index in [('body_x',0),('body_y',1)]:
        extrema[label]={key:{'frame': r['frame'],'timestamp_seconds':r['timestamp_seconds'],'value_px':r['silhouette_centroid_xy'][index]}
                        for key,func in [('minimum',min),('maximum',max)]
                        for r in [func(measured,key=lambda r:r['silhouette_centroid_xy'][index])]} if measured else {}
    result={'schema_version':1,'source_video':str(video),'source_sha256':timing['source_sha256'],
            'resolution':[width,height],'fps':fps,'frames':rows,'body_silhouette_extrema':extrema,
            'individual_leg_measurements':'UNVERIFIED; no tracks promoted from another video',
            'limitations':['Colored studio-background segmentation only.','Contours are not anatomical joint centers.',
                          'Leg labels, knee angles, foot lift and stride cannot be verified from these contours alone.']}
    (output/'measured_positions.json').write_text(json.dumps(result,indent=2))
    (output/'gait_timing.json').write_text(json.dumps(timing,indent=2))
    if images: cv2.imwrite(str(output/'measurement_review.jpg'),np.vstack(images))
    return {'measured_positions':str(output/'measured_positions.json'),'gait_timing':str(output/'gait_timing.json'),
            'measurement_review':str(output/'measurement_review.jpg'),'frames':len(rows),
            'timing_status':timing['status'],'joint_identity':'UNVERIFIED'}


if __name__ == '__main__':
    import sys
    print(json.dumps(analyze_manifest(sys.argv[1],sys.argv[2])))
