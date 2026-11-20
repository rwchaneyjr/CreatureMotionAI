"""Conservative 2D reference step-event analysis.

This module extracts candidate lift/stride events from a side-view hip/knee/foot
track. It never turns 2D observations into 3D foot targets or animation keys.
Only explicitly reviewed observations with a hash-bound identity approval are
eligible to be passed to a later constrained pose fitter.
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Any, Dict, List, Optional


_APPROVED_ROW_STATES = {"manual", "manually_reviewed", "approved", "observed_confirmed"}
_REQUIRED_LANDMARKS = ("hip", "knee", "ankle", "foot")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _point(row: Dict[str, Any], name: str) -> Optional[List[float]]:
    try:
        value = row["landmarks_2d"][name]
        x, y = float(value[0]), float(value[1])
        if math.isfinite(x) and math.isfinite(y):
            return [x, y]
    except (KeyError, TypeError, ValueError, IndexError):
        pass
    return None


def _landmark_is_reviewed(row: Dict[str, Any], name: str) -> bool:
    states = row.get("landmark_status", {})
    state = states.get(name) if isinstance(states, dict) else None
    if state is None:
        state = row.get("status", "")
    return str(state).strip().lower() in _APPROVED_ROW_STATES


def _identity_approval_valid(track_path: Path, approval_path: Optional[Path], leg: str,
                             track: Dict[str, Any]) -> Dict[str, Any]:
    if approval_path is None:
        return {"approved": False, "reason": "No explicit identity-review manifest supplied."}
    try:
        import json
        manifest = json.loads(approval_path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        return {"approved": False, "reason": f"Could not read approval manifest: {exc}"}
    expected_hash = sha256_file(track_path)
    source_video = track.get("source_video")
    expected_video_hash = track.get("source_video_sha256")
    source_prediction_path = track.get("source_prediction_track")
    source_prediction_hash = track.get("source_prediction_track_sha256")
    bound = manifest.get("track_sha256") == expected_hash
    video_bound = bool(source_video and expected_video_hash
                       and manifest.get("source_video") == source_video
                       and manifest.get("source_video_sha256") == expected_video_hash)
    prediction_bound = bool(source_prediction_path and source_prediction_hash
                            and manifest.get("source_prediction_track") == source_prediction_path
                            and manifest.get("source_prediction_track_sha256") == source_prediction_hash)
    accepted = (
        manifest.get("status") == "approved"
        and manifest.get("identity_verified") is True
        and manifest.get("leg") == leg
        and bound and video_bound and prediction_bound
    )
    return {
        "approved": accepted,
        "reason": "Identity, video, prediction source, and approved evidence hashes match." if accepted else
                  "Manifest must approve this leg and match the approved-track, source-video, and source-prediction hashes.",
        "track_sha256": expected_hash,
        "source_video_sha256": expected_video_hash,
        "source_prediction_track_sha256": source_prediction_hash,
        "manifest_leg": manifest.get("leg"),
        "manifest_status": manifest.get("status"),
    }


def analyze_reference_step_track(track: Dict[str, Any], track_path: Path,
                                 approval_path: Optional[Path] = None,
                                 confidence_floor: float = 0.60) -> Dict[str, Any]:
    """Summarize side-view step evidence without fabricating missing landmarks.

    The exported per-frame events remain provisional unless both the identity
    manifest and the individual hip/knee/foot observations are reviewed.
    """
    leg = str(track.get("leg", "UNNAMED"))
    identity = _identity_approval_valid(track_path, approval_path, leg, track)
    rows = sorted(track.get("frames", []), key=lambda item: int(item.get("frame", -1)))
    frames: List[Dict[str, Any]] = []
    for row in rows:
        points = {name: _point(row, name) for name in _REQUIRED_LANDMARKS}
        confidence = row.get("confidence", {})
        landmark_ok = all(
            points[name] is not None
            and _landmark_is_reviewed(row, name)
            and float(confidence.get(name, 0.0)) >= confidence_floor
            for name in _REQUIRED_LANDMARKS
        )
        hip, knee, ankle, foot = (points[name] for name in _REQUIRED_LANDMARKS)
        frames.append({
            "frame": int(row.get("frame", -1)),
            "row_status": row.get("status", "missing"),
            "source": row.get("source", "unknown"),
            "candidate_points_present": all(points.values()),
            "reviewed_points_valid": bool(landmark_ok),
            "confidence_min": min((float(confidence.get(n, 0.0)) for n in _REQUIRED_LANDMARKS), default=0.0),
            "hip_relative_foot_xy": [foot[0] - hip[0], foot[1] - hip[1]] if hip and foot else None,
            "knee_relative_hip_xy": [knee[0] - hip[0], knee[1] - hip[1]] if hip and knee else None,
            "ankle_relative_knee_xy": [ankle[0] - knee[0], ankle[1] - knee[1]] if ankle and knee else None,
            "event": "UNVERIFIED",
        })

    reviewed_count = sum(frame["reviewed_points_valid"] for frame in frames)
    # Event classification is deliberately limited to reviewed samples. Vertical
    # image movement is a lift candidate, not proof of world-space clearance.
    accepted = [frame for frame in frames if frame["reviewed_points_valid"]]
    if accepted:
        relative_y = [frame["hip_relative_foot_xy"][1] for frame in accepted]
        ordered = sorted(relative_y)
        ground_proxy = ordered[min(len(ordered) - 1, round(.85 * (len(ordered) - 1)))]
        excursion = max(relative_y) - min(relative_y)
        lift_threshold = max(2.0, excursion * .20)
        accepted_set = {frame["frame"] for frame in accepted}
        for frame in frames:
            if frame["frame"] not in accepted_set:
                continue
            rel_y = frame["hip_relative_foot_xy"][1]
            frame["event"] = "SWING_CANDIDATE" if rel_y < ground_proxy - lift_threshold else "STANCE_CANDIDATE"

    all_identity_and_observation_approved = identity["approved"] and reviewed_count == len(frames) and bool(frames)
    return {
        "schema_version": 1,
        "leg": leg,
        "fps": track.get("fps"),
        "source_track": str(track_path),
        "source_track_sha256": sha256_file(track_path),
        "identity_approval": identity,
        "coordinate_space": "2D image pixels; y increases downward",
        "interpretation": "Relative hip-to-foot events are visual candidates only; no calibrated ground, 3D contact, or IK target is inferred.",
        "status": "APPROVED_2D_EVENTS_READY_FOR_3D" if all_identity_and_observation_approved else "PROVISIONAL_ONLY",
        "eligible_for_3d_fit": bool(all_identity_and_observation_approved),
        "animation_use_allowed": False,
        "animation_candidate_allowed": False,
        "animation_blockers": ["Independent 3D pose fitting has not passed.",
                               "Anatomical reachability and joint-limit validation have not passed.",
                               "Physical validation (ground contact, deformation, and collision) has not passed."],
        "frames_total": len(frames),
        "frames_with_reviewed_hip_knee_foot": reviewed_count,
        "frames_candidate_only": sum(frame["candidate_points_present"] and not frame["reviewed_points_valid"] for frame in frames),
        "candidate_lift_excursion_px": (max((f["hip_relative_foot_xy"][1] for f in frames if f["hip_relative_foot_xy"] is not None), default=0.0)
                                         - min((f["hip_relative_foot_xy"][1] for f in frames if f["hip_relative_foot_xy"] is not None), default=0.0)),
        "frames": frames,
        "blockers": [] if all_identity_and_observation_approved else [
            reason for reason, active in ((identity["reason"], not identity["approved"]),
                                          ("One or more hip/knee/foot landmarks are not individually reviewed at sufficient confidence.", reviewed_count != len(frames))) if active
        ],
        "next_stage_requirements": [
            "After review, estimate side-view event timing only from approved observations.",
            "Feed approved 2D events to 3D reconstruction; use the existing FootContactTracker only after calibrated 3D sole points and anatomy constraints exist.",
            "2D approval never authorizes Action creation; independently pass 3D fitting, reachability, anatomy, and physical validation first.",
        ],
    }
