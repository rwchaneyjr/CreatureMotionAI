import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
pred_path = ROOT / 'data/generated/selected_video_dlc_frontL_predictions.json'
approved_path = ROOT / 'data/generated/frontL_selected_video_landmarks.json'
out = ROOT / 'data/generated/dlc_audit_20261116/dlc_outlier_audit.json'
out.parent.mkdir(parents=True, exist_ok=True)
p = json.loads(pred_path.read_text())
a = json.loads(approved_path.read_text())
names = ('hip', 'knee', 'ankle', 'foot')
rows = []
prev = None
for item in p['frames']:
    f = int(item['frame'])
    pts = {k: np.array(v, dtype=float) for k, v in item['landmarks_2d'].items()}
    cf = {k: float(v) for k, v in item['confidence'].items()}
    seg = np.array([np.linalg.norm(pts[x] - pts[y]) for x, y in zip(names, names[1:])])
    jump = float(max(np.linalg.norm(pts[k] - prev[k]) for k in names)) if prev else 0.0
    prev = pts
    mean_conf = float(np.mean([cf.get(k, 0) for k in names]))
    reasons = []
    score = 0.0
    if mean_conf < .6:
        reasons.append('low_mean_confidence')
        score += (0.6 - mean_conf) * 100
    if np.max(seg) / max(np.min(seg), 1e-6) > 3.5:
        reasons.append('implausible_segment_ratio')
        score += 25
    if jump > 80:
        reasons.append('large_temporal_jump')
        score += min(40, (jump - 80) / 2)
    approved = a.get('landmarks', {}).get(str(f))
    errors = {}
    if approved:
        for k in names:
            errors[k] = float(np.linalg.norm(pts[k] - np.array([approved[k]['x'], approved[k]['y']], dtype=float)))
        if max(errors.values()) > 35:
            reasons.append('large_error_vs_approved_label')
            score += min(40, (max(errors.values()) - 35) / 2)
    rows.append({'frame': f, 'mean_confidence': round(mean_conf, 4), 'segment_lengths_px': [round(float(x), 2) for x in seg], 'max_temporal_jump_px': round(jump, 2), 'approved_errors_px': errors, 'outlier_score': round(score, 3), 'reasons': reasons, 'status': 'REVIEW_REQUIRED' if reasons else 'SCREENED_OK'})
ranked = sorted(rows, key=lambda x: (-x['outlier_score'], x['frame']))
review = [r for r in ranked if r['status'] == 'REVIEW_REQUIRED']
def ranges(frames):
    out = []
    for f in sorted(frames):
        if not out or f != out[-1][-1] + 1:
            out.append([f])
        else:
            out[-1].append(f)
    return [[x[0], x[-1]] for x in out]
report = {'status': 'AUTOMATIC_DLC_AUDIT_COMPLETE', 'source_prediction_file': str(pred_path), 'approved_file': str(approved_path), 'coordinate_system': '640x720 left side panel; no training crop offset', 'frames_analyzed': len(rows), 'screened_ok_count': sum(r['status'] == 'SCREENED_OK' for r in rows), 'review_required_count': len(review), 'review_ranges': ranges(r['frame'] for r in review), 'physical_leg_identity': 'UNVERIFIED', 'approved_labels_modified': False, 'retraining': 'NOT_RUN', 'refinement_interface': 'NOT_OPENED; audit first', 'criteria': ['confidence', 'temporal continuity', 'segment-length ratio', 'error against approved labels where available'], 'ranked_suspicious_frames': ranked[:80]}
out.write_text(json.dumps(report, indent=2))
print(json.dumps({'out': str(out), 'frames_analyzed': len(rows), 'screened_ok': report['screened_ok_count'], 'review_required': len(review), 'review_ranges': report['review_ranges'], 'top_frames': [r['frame'] for r in ranked[:20]]}, indent=2))
