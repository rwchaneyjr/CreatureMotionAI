"""Anatomical sole extraction and confidence-aware world-space foot locking.

The state machine is leg-count agnostic. Blender callers supply explicit chains
from an anatomy profile; sole samples come from evaluated, weighted mesh vertices
and downward-facing surface normals rather than bone endpoints or proxy spheres.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence
import numpy as np

from .contact_states import ContactConfig, ContactDecision, FootContactTracker


@dataclass(frozen=True)
class SolePatch:
    vertex_indices: np.ndarray
    sample_frame: int
    min_clearance: float
    quality: float
    extent_xyz: tuple[float, float, float]


def select_sole_patch(candidates: Iterable[dict], *, minimum_vertices: int = 12,
                      maximum_thickness: float = 0.006) -> SolePatch:
    """Choose a real downward-facing mesh patch closest to ground in a cycle.

    Each candidate contains frame, vertex_indices, world_positions, clearance,
    and underside_fraction. The chosen indices remain fixed for all measurements.
    """
    viable = []
    for row in candidates:
        ids = np.asarray(row["vertex_indices"], dtype=np.int64)
        points = np.asarray(row["world_positions"], dtype=float)
        if len(ids) < minimum_vertices or points.shape != (len(ids), 3):
            continue
        extent = np.ptp(points, axis=0)
        if extent[2] > maximum_thickness:
            continue
        clearance = float(row["clearance"])
        underside = float(row.get("underside_fraction", 1.0))
        # A tiny penetration is tolerated as mesh/ground numerical noise.
        ground_score = max(0.0, 1.0 - abs(clearance) / 0.025)
        compactness = max(0.0, 1.0 - extent[2] / maximum_thickness)
        quality = min(1.0, len(ids) / 40.0) * underside * ground_score * (0.5 + 0.5 * compactness)
        viable.append((quality, row, ids, extent))
    if not viable:
        raise ValueError("No anatomically supported sole patch met geometry criteria")
    quality, row, ids, extent = max(viable, key=lambda item: item[0])
    return SolePatch(ids, int(row["frame"]), float(row["clearance"]),
                     float(quality), tuple(float(v) for v in extent))


def make_tracker(config: ContactConfig | None = None) -> FootContactTracker:
    """Create independent state for one configured limb."""
    return FootContactTracker(config or ContactConfig())


def centroid_world(world_vertices: np.ndarray, patch: SolePatch) -> np.ndarray:
    """Return the fixed anatomical sole patch centroid for one evaluated frame."""
    return np.asarray(world_vertices, dtype=float)[patch.vertex_indices].mean(axis=0)


def patch_clearance(world_vertices: np.ndarray, patch: SolePatch, ground_z: float) -> float:
    """Minimum sole-patch height above a horizontal ground plane."""
    return float(np.asarray(world_vertices, dtype=float)[patch.vertex_indices, 2].min() - ground_z)


def stance_slip(points: Sequence[Sequence[float]], states: Sequence[str]) -> dict:
    """Planar path length and peak per-frame slip over consecutive stance pairs."""
    distances = []
    for i in range(1, min(len(points), len(states))):
        if states[i - 1] == "STANCE" and states[i] == "STANCE":
            a, b = np.asarray(points[i - 1], float), np.asarray(points[i], float)
            distances.append(float(np.linalg.norm((b - a)[:2])))
    return {"stance_pairs": len(distances), "planar_path_length": float(sum(distances)),
            "max_per_frame_slip": float(max(distances, default=0.0)),
            "mean_per_frame_slip": float(np.mean(distances)) if distances else None}
