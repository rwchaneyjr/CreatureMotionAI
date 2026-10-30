"""Creature-independent 2D segment pose targets.

This module does not know Blender bone names. It converts tracked point pairs
into stable angles that a Blender adapter can apply to mapped chains.
"""
import math


def segment_angle(start, end, invert_y=True):
    dx = float(end[0]) - float(start[0])
    dy = float(end[1]) - float(start[1])
    if invert_y:
        dy = -dy
    if abs(dx) < 1e-8 and abs(dy) < 1e-8:
        return None
    return math.atan2(dy, dx)


def solve_segments(frame, assignments):
    """Return pose targets for assignments with landmark_start/end fields.

    Assignments are profile data, for example:
    {"bone": "Leg_Front.L_01", "landmark_start": "hip_left",
     "landmark_end": "knee_left", "weight": 1.0}
    """
    landmarks = frame.get("landmarks", {})
    targets = []
    for assignment in assignments:
        start = landmarks.get(assignment.get("landmark_start"))
        end = landmarks.get(assignment.get("landmark_end"))
        if not start or not end:
            continue
        angle = segment_angle(start, end)
        if angle is not None:
            targets.append({
                "bone": assignment["bone"],
                "rotation_z": angle * float(assignment.get("weight", 1.0)),
            })
    return targets
