"""Configurable, rest-relative joint limits for experimental gait generation.

Limits are opt-in: existing solvers keep their current behavior unless a
profile is explicitly loaded. Values are radians and are applied per bone.
"""
from __future__ import annotations
import json
from pathlib import Path

DEFAULT_PROFILE = {
    "mode": "relaxed_diagnostic",
    "tolerance": 0.02,
    "joints": {},
}

def load_profile(path: str | Path | None = None) -> dict:
    if not path:
        return dict(DEFAULT_PROFILE)
    p = Path(path)
    if not p.exists():
        return dict(DEFAULT_PROFILE)
    data = json.loads(p.read_text(encoding="utf-8"))
    out = dict(DEFAULT_PROFILE)
    out.update(data)
    out["joints"] = dict(DEFAULT_PROFILE["joints"], **data.get("joints", {}))
    return out

def clamp_angle(value: float, bone: str, axis: str, profile: dict) -> float:
    spec = profile.get("joints", {}).get(bone, {}).get(axis)
    if not spec:
        return value
    lo, hi = float(spec[0]), float(spec[1])
    tol = float(profile.get("tolerance", 0.0))
    return max(lo - tol, min(hi + tol, value))

def clamp_euler(euler, bone: str, profile: dict):
    for i, axis in enumerate(("x", "y", "z")):
        euler[i] = clamp_angle(float(euler[i]), bone, axis, profile)
    return euler
