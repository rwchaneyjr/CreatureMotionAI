"""Generic adapter from confidence-scored tracked 3D landmarks to leg solvers."""
from mathutils import Vector

def adapt_tracked_leg(landmarks, confidence, armature_world, min_confidence=0.75):
    required = ("hip", "knee", "ankle", "foot")
    missing = [name for name in required if name not in landmarks or confidence.get(name, 0.0) < min_confidence]
    if missing:
        return {"status": "UNCERTAIN", "missing_or_low_confidence": missing}
    points = {name: armature_world @ Vector(landmarks[name]) for name in required}
    lengths = [(points["knee"] - points["hip"]).length, (points["ankle"] - points["knee"]).length]
    if min(lengths) <= 1e-8:
        return {"status": "REJECTED", "reason": "degenerate_landmark_chain"}
    return {"status": "PASS", "points_world": {k: list(v) for k, v in points.items()}, "confidence": dict(confidence), "observed_lengths": lengths}

def reject_if_inconsistent(adapted, reference_lengths, tolerance_ratio=0.15):
    if adapted.get("status") != "PASS":
        return adapted
    bad = [i for i, (observed, reference) in enumerate(zip(adapted["observed_lengths"], reference_lengths)) if abs(observed-reference) > reference*tolerance_ratio]
    return {**adapted, "status": "REJECTED" if bad else "PASS", "length_mismatch_segments": bad}
