"""Persistent, view-independent pose observations for CreatureMotionAI.

This is deliberately additive: older landmark JSON files remain readable and
their approval/status fields are copied without reinterpretation.
"""
from __future__ import annotations
import json
from pathlib import Path

SCHEMA = "cmai_pose_library_v1"

def load(path):
    p = Path(path)
    if not p.exists():
        return {"schema": SCHEMA, "observations": [], "poses": []}
    data = json.loads(p.read_text(encoding="utf-8"))
    data.setdefault("schema", SCHEMA)
    data.setdefault("observations", [])
    # Older files used ``approved_poses``. Keep both spellings readable.
    if "poses" not in data and "approved_poses" in data:
        data["poses"] = data["approved_poses"]
    data.setdefault("poses", [])
    data.setdefault("approved_poses", data["poses"])
    return data

def save(path, data):
    data["approved_poses"] = data.get("poses", [])
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

def add_observation(data, *, source_video, frame, view, landmarks, confidence=None,
                    approval_status="unreviewed"):
    row = {
        "source_video": str(source_video), "frame": int(frame), "view": str(view),
        "landmarks": landmarks, "confidence": confidence or {},
        "approval_status": approval_status,
    }
    rows = data.setdefault("observations", [])
    # Merge corrections into the same source/frame/view record instead of
    # creating duplicates when a review is reopened.
    for existing in rows:
        if (existing.get("source_video") == str(source_video)
                and int(existing.get("frame", -1)) == int(frame)
                and existing.get("view") == str(view)):
            existing.setdefault("landmarks", {}).update(landmarks)
            existing.setdefault("confidence", {}).update(confidence or {})
            existing["approval_status"] = approval_status
            return existing
    rows.append(row)
    return row

def add_approved_pose(data, *, source_frame, rotations, armature=None,
                      foot_orientation=None, metadata=None):
    row = {
        "source_frame": int(source_frame), "armature": armature,
        "rotations": rotations, "foot_orientation": foot_orientation or {},
        "approval_status": "approved", "metadata": metadata or {},
    }
    data.setdefault("poses", []).append(row)
    return row

def observations(data, *, view=None, source_video=None, approved_only=False):
    rows = data.get("observations", [])
    if view is not None: rows = [x for x in rows if x.get("view") == view]
    if source_video is not None: rows = [x for x in rows if x.get("source_video") == str(source_video)]
    if approved_only: rows = [x for x in rows if x.get("approval_status") in ("manual_verified", "approved")]
    return list(rows)

def poses_by_side_frame(data, approved_only=True):
    rows = data.get("poses", [])
    if approved_only: rows = [x for x in rows if x.get("approval_status") == "approved"]
    return sorted(rows, key=lambda x: int(x.get("source_frame", 0)))

def side_view_fk_input(data, source_video=None):
    """Read-only adapter for the existing FK input shape; no depth is added."""
    rows = observations(data, view="side", source_video=source_video, approved_only=True)
    return [{"frame": int(x["frame"]), "landmarks": x.get("landmarks", {}),
             "confidence": x.get("confidence", {}), "depth": "unknown",
             "approval_status": x.get("approval_status")} for x in sorted(rows, key=lambda r: int(r["frame"]))]
