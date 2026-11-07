"""Readiness and input adapter for whole-body static pose fitting.

This module deliberately does not invent depth or hidden joints.  It accepts
approved observations from the pose library and returns only visible inputs
that can be passed to a future rest-relative FK fitter.
"""
from __future__ import annotations

from .pose_library import observations


def capture_rest_state(armature, mesh=None):
    """Capture evaluated rest matrices and mesh coordinates for a temporary copy."""
    result = {"armature": armature.name, "bones": {}, "mesh": None}
    for bone in armature.pose.bones:
        world = armature.matrix_world @ bone.matrix
        result["bones"][bone.name] = {
            "matrix_world": [list(row) for row in world],
            "head": list(armature.matrix_world @ bone.head),
            "tail": list(armature.matrix_world @ bone.tail),
        }
    if mesh is not None:
        result["mesh"] = {"name": mesh.name, "vertex_count": len(mesh.data.vertices),
                           "modifier_armatures": [m.object.name for m in mesh.modifiers
                                                   if m.type == "ARMATURE" and m.object]}
    return result


def validate_rest_state(armature, captured, tolerance=1e-5):
    """Compare evaluated world-space bone endpoints after a pose application."""
    from mathutils import Vector
    failures = []
    for name, row in captured.get("bones", {}).items():
        bone = armature.pose.bones.get(name)
        if bone is None:
            failures.append({"bone": name, "reason": "missing_bone"})
            continue
        head = armature.matrix_world @ bone.head
        tail = armature.matrix_world @ bone.tail
        he = (head - Vector(row["head"])).length
        te = (tail - Vector(row["tail"])).length
        if max(he, te) > tolerance:
            failures.append({"bone": name, "head_error": he, "tail_error": te})
    return {"status": "PASS" if not failures else "FAIL", "tolerance": tolerance, "failures": failures}


def approved_visible_inputs(data, *, source_video, frame, view="side"):
    rows = observations(data, view=view, source_video=source_video, approved_only=True)
    rows = [r for r in rows if int(r.get("frame", -1)) == int(frame)]
    points = {}
    for row in rows:
        for name, point in row.get("landmarks", {}).items():
            if point.get("visible", True):
                points[name] = {
                    "x": float(point["x"]), "y": float(point["y"]),
                    "confidence": float(row.get("confidence", {}).get(name, 1.0)),
                    "approval_status": row.get("approval_status"),
                }
    return points


def static_fit_readiness(data, *, source_video, frame, view="side"):
    points = approved_visible_inputs(data, source_video=source_video, frame=frame, view=view)
    # Body fitting can proceed with incomplete data, but must say exactly what
    # remains unknown rather than treating a missing joint as a target.
    body = {n: points[n] for n in ("body_center", "snout", "tail_base") if n in points}
    leg = {n: points[n] for n in ("hip", "knee", "ankle", "foot") if n in points}
    missing = [n for n in ("body_center", "snout", "tail_base") if n not in body]
    return {
        "status": "READY_FOR_BOUNDED_STATIC_FIT" if len(body) >= 2 or leg else "BLOCKED_NO_APPROVED_VISIBLE_INPUTS",
        "source_video": str(source_video), "frame": int(frame), "view": view,
        "visible_approved_points": points, "body_points": body, "leg_points": leg,
        "missing_body_points": missing,
        "depth": "unknown",
        "constraints": ["rest-relative FK", "original bone lengths", "unknown joints are not invented"],
    }
