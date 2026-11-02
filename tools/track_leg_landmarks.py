"""Track reviewed two-camera leg landmarks through a short reference segment.

Keyframe points are never invented: only visible keyframe points seed optical
flow. Failed tracks become uncertain and are excluded from triangulation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def read_frames(video: Path, limit: int) -> dict[int, tuple[np.ndarray, np.ndarray]]:
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open {video}")
    out = {}
    for number in range(1, limit + 1):
        ok, frame = cap.read()
        if not ok:
            break
        half = frame.shape[1] // 2
        out[number] = (frame[:, :half], frame[:, half:])
    cap.release()
    return out


def load_seeds(path: Path) -> dict[int, dict[str, dict[str, dict]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    seeds = {}
    for row in data.get("frames", []):
        frame = int(row["frame"])
        if "points" in row:
            cameras = {"camera_A": {}, "camera_B": {}}
            for point in row["points"]:
                for camera in cameras:
                    item = point.get(camera, {})
                    cameras[camera][point["name"]] = {**item, "leg": point.get("leg"), "state": item.get("state", "uncertain")}
            seeds[frame] = cameras
        else:
            seeds[frame] = {camera: row.get(camera, {}).get("landmarks", {}) for camera in ("camera_A", "camera_B")}
    return seeds


def track_one(prev: dict, image_a: np.ndarray, image_b: np.ndarray, image_width: int, image_height: int) -> dict:
    valid = {name: item for name, item in prev.items() if item.get("visible") and item.get("state") not in ("uncertain", "estimated")}
    if not valid:
        return {name: {**item, "state": "uncertain_no_seed", "visible": False} for name, item in prev.items()}
    names = list(valid)
    p0 = np.float32([[valid[name]["x"], valid[name]["y"]] for name in names]).reshape(-1, 1, 2)
    p1, status, errors = cv2.calcOpticalFlowPyrLK(image_a, image_b, p0, None)
    result = {name: {**item, "state": "uncertain_tracking_failed", "visible": False} for name, item in prev.items()}
    for name, point, ok, error in zip(names, p1.reshape(-1, 2), status.reshape(-1), errors.reshape(-1)):
        x, y = map(float, point)
        jump = float(np.linalg.norm(point - p0[names.index(name), 0]))
        good = bool(ok and error < 25.0 and jump < 90.0 and 0 <= x < image_width and 0 <= y < image_height)
        if good:
            result[name] = {**valid[name], "x": x, "y": y, "state": "optical_flow", "visible": True, "confidence": float(valid[name].get("confidence", 0.0)) * 0.92, "flow_error": float(error), "jump_px": jump}
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("seeds", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-frames", type=int, default=24)
    args = parser.parse_args()
    images = read_frames(args.video, args.max_frames)
    seeds = load_seeds(args.seeds)
    if not images:
        raise RuntimeError("No video frames available")
    keyframes = sorted(x for x in seeds if x in images)
    if not keyframes:
        raise RuntimeError("No seed frames overlap the available video")
    rows = []
    current = {"camera_A": {}, "camera_B": {}}
    for frame_number in range(1, min(args.max_frames, max(images)) + 1):
        if frame_number in seeds:
            current = seeds[frame_number]
            row_state = "keyframe_seed"
        elif rows:
            previous_images = images[frame_number - 1]
            current = {camera: track_one(current[camera], previous_images[0], images[frame_number][0], images[frame_number][0].shape[1], images[frame_number][0].shape[0]) if camera == "camera_A" else track_one(current[camera], previous_images[1], images[frame_number][1], images[frame_number][1].shape[1], images[frame_number][1].shape[0]) for camera in ("camera_A", "camera_B")}
            row_state = "optical_flow"
        rows.append({"frame": frame_number, "camera_A": {"landmarks": current["camera_A"]}, "camera_B": {"landmarks": current["camera_B"]}, "state": row_state})
    result = {"status": "provisional_identity_tracking", "frames": rows, "keyframes": keyframes, "source_seeds": str(args.seeds.resolve()), "note": "Optical-flow tracks are provisional. Hidden or failed points remain uncertain and must not be triangulated without two-view confirmation."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    visible = sum(sum(int(x.get("visible", False)) for x in row["camera_A"]["landmarks"].values()) + sum(int(x.get("visible", False)) for x in row["camera_B"]["landmarks"].values()) for row in rows)
    print(json.dumps({"output": str(args.output), "frames": len(rows), "keyframes": keyframes, "visible_observations": visible}, indent=2))


if __name__ == "__main__":
    main()
