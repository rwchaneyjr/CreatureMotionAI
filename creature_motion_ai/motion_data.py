"""Portable normalized landmark data exchanged by analysis backends and solvers."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Landmark:
    name: str
    x: float
    y: float
    z: float = 0.0
    confidence: float = 1.0


def validate_frame(frame):
    required = {"frame", "landmarks"}
    missing = required.difference(frame)
    if missing:
        raise ValueError(f"Missing frame fields: {sorted(missing)}")
    if not isinstance(frame["landmarks"], dict):
        raise ValueError("landmarks must be a name-to-point mapping")
    return True
