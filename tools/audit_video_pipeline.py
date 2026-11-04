import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
def read(name):
    p=root/'data'/'generated'/name
    return json.loads(p.read_text()) if p.exists() else None
report={
 'video': {'file': str(root/'data/reference/goodspilitbalisk.mp4'), 'present': (root/'data/reference/goodspilitbalisk.mp4').exists()},
 'tracking': {'single_camera_tracks': 'PRESENT_PROVISIONAL', 'review_candidates': read('single_camera_review_candidates_24.json') is not None, 'dino_detector': read('dino_balisk_detector.json') is not None, 'confidence_scored_3d_tracks': False},
 'calibration': {'synthetic': read('synthetic_camera_calibration.json') is not None, 'real_two_view': 'FAIL_SYNC_NOT_ESTABLISHED'},
 'triangulation': {'synthetic': 'PASS', 'real_video': 'BLOCKED'},
 'identity_tracking': {'eight_leg_identity': 'PROVISIONAL', 'validated_real_video': False},
 'adapter': {'module': 'creature_motion_ai/video_solver_adapter.py', 'status': 'IMPLEMENTED_REQUIRES_CONFIDENT_3D_INPUT'},
 'decision': 'STOP_BEFORE_VIDEO_DERIVED_ACTION',
 'missing': ['reliable synchronized two-view calibration or verified single-camera depth', 'confidence-scored hip/knee/ankle/foot 3D landmarks for one leg']
}
(root/'data/generated/video_tracking_pipeline_audit.json').write_text(json.dumps(report,indent=2))
