"""Checks reviewed-evidence gating and relative lift candidates."""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from creature_motion_ai.reference_step_events import analyze_reference_step_track, sha256_file


def make_track(status, video_path, prediction_path):
    foot_y = (10, 4, 10, 10)
    return {"leg": "Leg_Rear.L", "fps": 24,
            "source_video": str(video_path), "source_video_sha256": sha256_file(video_path),
            "source_prediction_track": str(prediction_path),
            "source_prediction_track_sha256": sha256_file(prediction_path), "frames": [
        {"frame": i + 1, "status": status, "source": "test",
         "landmarks_2d": {"hip": [0, 0], "knee": [4, 5], "ankle": [6, 7], "foot": [8, foot_y[i]]},
         "confidence": {"hip": .9, "knee": .9, "ankle": .9, "foot": .9}}
        for i in range(4)
    ]}


test_tmp = ROOT / "data" / "cache" / "reference_step_test"
test_tmp.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(dir=test_tmp) as directory:
    root = Path(directory)
    video = root / "source.mp4"; video.write_bytes(b"video identifier")
    prediction = root / "prediction.json"; prediction.write_text('{"candidate":true}', encoding="utf-8")
    path = root / "track.json"
    path.write_text(json.dumps(make_track("prediction", video, prediction)), encoding="utf-8")
    unapproved = analyze_reference_step_track(json.loads(path.read_text()), path)
    assert unapproved["status"] == "PROVISIONAL_ONLY"
    assert not unapproved["animation_use_allowed"]
    assert unapproved["frames_with_reviewed_hip_knee_foot"] == 0

    reviewed_track = make_track("manually_reviewed", video, prediction)
    path.write_text(json.dumps(reviewed_track), encoding="utf-8")
    manifest_path = root / "approval.json"
    manifest_path.write_text(json.dumps({
        "status": "approved", "identity_verified": True,
        "leg": "Leg_Rear.L", "track_sha256": sha256_file(path),
        "source_video": str(video), "source_video_sha256": sha256_file(video),
        "source_prediction_track": str(prediction),
        "source_prediction_track_sha256": sha256_file(prediction),
    }), encoding="utf-8")
    approved = analyze_reference_step_track(reviewed_track, path, manifest_path)
    assert approved["status"] == "APPROVED_2D_EVENTS_READY_FOR_3D"
    assert approved["eligible_for_3d_fit"]
    assert not approved["animation_use_allowed"]
    assert approved["frames"][1]["event"] == "SWING_CANDIDATE"
    assert approved["frames"][0]["event"] == "STANCE_CANDIDATE"

    manifest_path.write_text(json.dumps({
        "status": "approved", "identity_verified": True,
        "leg": "Leg_Front.L", "track_sha256": sha256_file(path),
        "source_video": str(video), "source_video_sha256": sha256_file(video),
        "source_prediction_track": str(prediction),
        "source_prediction_track_sha256": sha256_file(prediction),
    }), encoding="utf-8")
    wrong_identity = analyze_reference_step_track(reviewed_track, path, manifest_path)
    assert wrong_identity["status"] == "PROVISIONAL_ONLY"
    assert not wrong_identity["animation_use_allowed"]

print("PASS: predictions remain provisional; reviewed relative lift is detected; wrong leg approval is rejected")
