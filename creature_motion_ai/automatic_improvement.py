"""Automatic, conservative reference-guided improvement gate.

This module never promotes uncertain video tracking to ground truth. It
produces a confidence report and returns the validated baseline when the
evidence is insufficient for a safe correction.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

JOINTS = ("hip", "knee", "ankle", "foot")


def classify_tracking(prediction_path: str | Path, confidence_threshold: float = .6) -> dict[str, Any]:
    data = json.loads(Path(prediction_path).read_text(encoding="utf-8"))
    rows = data.get("frames", [])
    reliable = []
    uncertain = []
    for row in rows:
        conf = row.get("confidence", {})
        points = row.get("landmarks_2d", {})
        complete = all(j in points for j in JOINTS)
        score = min((float(conf.get(j, 0.0)) for j in JOINTS), default=0.0)
        item = {"frame": int(row.get("frame", 0)), "min_confidence": score, "complete": complete}
        (reliable if complete and score >= confidence_threshold else uncertain).append(item)
    runs: list[list[int]] = []
    for item in reliable:
        f = item["frame"]
        if not runs or f != runs[-1][-1] + 1:
            runs.append([f])
        else:
            runs[-1].append(f)
    continuous = [r for r in runs if len(r) >= 4]
    gaps = [b[0] - a[-1] - 1 for a, b in zip(continuous, continuous[1:])]
    # Separate islands cannot prove leg identity; require short occlusion gaps
    # before allowing a provisional candidate to influence animation.
    identity_status = "UNVERIFIED" if len(continuous) < 2 or any(g > 8 for g in gaps) else "PROVISIONAL"
    return {
        "status": "PASS_WITH_FALLBACK" if identity_status == "UNVERIFIED" else "TRACKING_CANDIDATE",
        "source": str(Path(prediction_path).resolve()),
        "frames": len(rows), "reliable_count": len(reliable),
        "uncertain_count": len(rows) - len(reliable), "reliable_runs": runs,
        "continuous_runs": continuous, "identity": identity_status,
        "gaps_between_runs": gaps,
        "fallback": identity_status == "UNVERIFIED",
        "reason": "Insufficient continuous evidence to prove one physical leg across gaps." if identity_status == "UNVERIFIED" else "Candidate requires geometric consistency check before promotion.",
    }


def choose_candidate(baseline: dict[str, Any], candidate: dict[str, Any], tracking: dict[str, Any]) -> dict[str, Any]:
    safe = bool(candidate.get("validation_passed")) and not bool(candidate.get("new_mesh_collisions"))
    improved = float(candidate.get("side_error", float("inf"))) < float(baseline.get("side_error", float("inf")))
    accepted = safe and improved and not tracking.get("fallback", True)
    return {"accepted": accepted, "reason": "accepted" if accepted else ("tracking_fallback" if tracking.get("fallback") else "candidate_not_better_or_unsafe")}


def compare_reference_curves(reference: list[float], candidate: list[float], max_offset: int = 30) -> dict[str, Any]:
    """Compare coarse motion curves without assigning individual legs."""
    import numpy as np
    n = min(len(reference), len(candidate))
    scores = []
    for offset in range(-max_offset, max_offset + 1):
        x, y = [], []
        for i in range(n):
            j = i + offset
            if 0 <= j < n:
                x.append(reference[i]); y.append(candidate[j])
        score = float(np.corrcoef(x, y)[0, 1]) if len(x) > 3 and np.std(x) and np.std(y) else -1.0
        scores.append((score, offset))
    score, offset = max(scores)
    return {"correlation": score, "phase_offset_frames": offset, "frames_compared": n, "identity_free": True}

