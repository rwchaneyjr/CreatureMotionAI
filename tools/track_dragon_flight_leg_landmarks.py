"""Create a review overlay for clearly visible near-side dragon leg landmarks.

Seed points are manually estimated on reference frame 121. Lucas-Kanade optical
flow propagates them; failed/ambiguous tracks are omitted from the overlay and
reported as uncertain. This is a review aid, not ground-truth annotation.
"""
from pathlib import Path
import json

import cv2
import numpy as np


VIDEO = Path(r"C:\Users\rober\Desktop\dragon fly feet tucked !~.mp4")
OUT = Path(__file__).resolve().parents[1] / "data/generated/dragon_quadruped_compatibility/fly_and_land"
ANCHOR = 120  # zero-based, source frame 121
COLORS = {
    "front": (40, 220, 255),  # BGR gold
    "rear": (255, 100, 230),  # BGR magenta
}
JOINTS = ("HIP", "KNEE", "ANKLE", "FOOT")
# Approximate visible near-side chain centers measured on frame 121 (1280x720).
SEEDS = {
    "front": [(503, 452), (499, 526), (512, 580), (535, 608)],
    "rear": [(657, 465), (686, 545), (715, 590), (760, 619)],
}


def lk_track(gray_frames, seed, start, direction):
    n = len(gray_frames)
    result = [None] * n
    result[start] = (np.asarray(seed, np.float32).reshape(1, 2), 0.0)
    point = np.asarray(seed, np.float32).reshape(1, 1, 2)
    for i in range(start, n - 1 if direction > 0 else 0, direction):
        j = i + direction
        nxt, status, err = cv2.calcOpticalFlowPyrLK(
            gray_frames[i], gray_frames[j], point, None,
            winSize=(25, 25), maxLevel=4,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01),
        )
        if nxt is None or status is None or not int(status[0, 0]):
            break
        back, back_status, _ = cv2.calcOpticalFlowPyrLK(
            gray_frames[j], gray_frames[i], nxt, None,
            winSize=(25, 25), maxLevel=4,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01),
        )
        xy = nxt[0, 0]
        roundtrip = float(np.linalg.norm(back[0, 0] - point[0, 0])) if back is not None else 999.0
        height, width = gray_frames[j].shape
        flow_error = float(err[0, 0]) if err is not None else 999.0
        valid = (back_status is not None and int(back_status[0, 0]) and roundtrip <= 4.0
                 and flow_error <= 55.0 and 0 <= xy[0] < width and 0 <= xy[1] < height)
        if not valid:
            break
        confidence = float(max(0.0, min(1.0, (1.0 - roundtrip / 4.0) * (1.0 - flow_error / 70.0))))
        result[j] = (xy.reshape(1, 2).copy(), confidence)
        point = nxt
    return result


def main():
    if not VIDEO.is_file():
        raise FileNotFoundError(VIDEO)
    OUT.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(VIDEO))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open {VIDEO}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frames.append(frame)
    cap.release()
    if ANCHOR >= len(frames):
        raise RuntimeError(f"Anchor frame {ANCHOR+1} missing from {len(frames)} frames")
    grays = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in frames]
    tracks = {}
    for leg, points in SEEDS.items():
        tracks[leg] = {}
        for joint, seed in zip(JOINTS, points):
            forward = lk_track(grays, seed, ANCHOR, 1)
            backward = lk_track(grays, seed, ANCHOR, -1)
            tracks[leg][joint] = [backward[k] if backward[k] is not None else forward[k] for k in range(len(frames))]

    output = OUT / "dragon_fly_feet_tuck_reference_marked.mp4"
    h, w = frames[0].shape[:2]
    writer = cv2.VideoWriter(str(output), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    if not writer.isOpened():
        raise RuntimeError(f"Could not write {output}")
    summary = {}
    for leg, by_joint in tracks.items():
        summary[leg] = {}
        for joint, values in by_joint.items():
            valid = [v for v in values if v is not None]
            summary[leg][joint] = {
                "state": "OPTICAL_FLOW_ESTIMATE" if valid else "UNCERTAIN",
                "tracked_frames": len(valid), "total_frames": len(frames),
                "anchor_frame": ANCHOR + 1,
                "anchor_xy_pixels": list(SEEDS[leg][JOINTS.index(joint)]),
            }
    for fi, frame in enumerate(frames):
        canvas = frame.copy()
        for leg, by_joint in tracks.items():
            color = COLORS[leg]
            for joint, values in by_joint.items():
                value = values[fi]
                if value is None:
                    continue
                x, y = np.round(value[0][0]).astype(int)
                confidence = value[1]
                if confidence < 0.12 and fi != ANCHOR:
                    continue
                cv2.drawMarker(canvas, (x, y), color, cv2.MARKER_TILTED_CROSS, 22, 3)
                short = {"HIP":"H", "KNEE":"K", "ANKLE":"A", "FOOT":"F"}[joint]
                cv2.putText(canvas, f"{leg[0].upper()}-{short}", (x + 8, y - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)
        cv2.putText(canvas, "Near-side visible leg landmarks | optical-flow proposals; review before use",
                    (20, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.68, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(canvas, f"Frame {fi+1}/{len(frames)}", (20, 64),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 2, cv2.LINE_AA)
        writer.write(canvas)
    writer.release()
    report = {
        "status": "REVIEW_OVERLAY_CREATED_ESTIMATES_NOT_APPROVED",
        "source_video": str(VIDEO), "source_fps": fps, "source_frames": len(frames),
        "output_video": str(output), "anchor_frame": ANCHOR + 1,
        "visibility_policy": "Only two near-side leg chains visible at the anchor are seeded. Far-side legs are not marked.",
        "method": "Manual seed estimates on frame 121, propagated forward/backward by pyramidal Lucas-Kanade with forward-backward consistency gate. Failed tracks are omitted.",
        "limitations": "Optical-flow tracks may drift or be occluded; every point remains an estimate until visually reviewed. This single-view video does not establish hidden far-side joint positions.",
        "landmarks": summary,
    }
    (OUT / "dragon_fly_feet_tuck_landmark_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"video": str(output), "report": str(OUT / 'dragon_fly_feet_tuck_landmark_report.json'), "landmarks": summary}, indent=2))


if __name__ == "__main__":
    main()
