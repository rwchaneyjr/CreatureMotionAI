import json
from pathlib import Path
import numpy as np

root = Path(__file__).resolve().parents[1]
pred = json.loads((root / 'data/generated/selected_video_dlc_frontL_predictions.json').read_text())
rows = []; prev = None
for item in pred['frames']:
    f = int(item['frame']); p = {k: np.array(v, float) for k, v in item['landmarks_2d'].items()}; c = {k: float(v) for k, v in item['confidence'].items()}
    seg = [float(np.linalg.norm(p[a] - p[b])) for a, b in zip(('hip','knee','ankle'), ('knee','ankle','foot'))]
    mean = float(np.mean([c.get(k, 0) for k in ('hip','knee','ankle','foot')]))
    jump = float(max(np.linalg.norm(p[k] - prev[k]) for k in p)) if prev else 0
    prev = p
    score = mean * 100 - max(0, (max(seg) / max(min(seg), 1e-6) - 3.0)) * 8 - max(0, jump - 80) * .08
    good = mean >= .72 and max(seg) / max(min(seg), 1e-6) < 3.5 and jump < 80
    rows.append({'frame': f, 'score': round(score, 3), 'mean_confidence': round(mean, 4), 'segment_lengths_px': [round(x, 2) for x in seg], 'max_jump_px': round(jump, 2), 'clear_candidate': good})
candidates = sorted([r for r in rows if r['clear_candidate']], key=lambda r: -r['score'])
selected = []
for row in candidates:
    if all(abs(row['frame'] - x['frame']) >= 8 for x in selected):
        selected.append(row)
    if len(selected) >= 5:
        break
out = root / 'data/generated/reference_leg_review/clear_frames.json'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({'status': 'CLEAR_FRAME_SELECTION', 'coordinate_system': '640x720 left side panel', 'selected_frames': selected, 'candidate_count': len(candidates), 'selection_policy': 'confidence, segment plausibility, temporal continuity, minimum 8-frame spacing'}, indent=2))
print(json.dumps({'selected_frames': [x['frame'] for x in selected], 'candidate_count': len(candidates), 'out': str(out)}))
