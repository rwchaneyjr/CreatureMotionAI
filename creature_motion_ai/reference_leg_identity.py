"""Prepare hash-bound, prediction-only landmark reviews for Blender."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, List


LANDMARKS = ("hip", "knee", "ankle", "foot")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _frame_score(row: Dict[str, Any]) -> tuple[float, float]:
    points = row.get("landmarks_2d", {})
    confidence = row.get("confidence", {})
    try:
        values = [float(confidence[name]) for name in LANDMARKS]
        coords = {name: [float(v) for v in points[name][:2]] for name in LANDMARKS}
        if not all(math.isfinite(v) for xy in coords.values() for v in xy):
            return -1.0, 0.0
        lengths = [math.dist(coords[a], coords[b]) for a, b in zip(LANDMARKS, LANDMARKS[1:])]
        ratio = max(lengths) / max(min(lengths), 1e-6)
        # Ranking only: confidence and a loose geometry sanity penalty. This
        # never changes or approves the model's proposed coordinates.
        score = min(values) * 0.75 + sum(values) / len(values) * 0.25
        score -= max(0.0, ratio - 5.0) * 0.035
        return score, min(values)
    except (KeyError, TypeError, ValueError, IndexError):
        return -1.0, 0.0


def select_review_frames(rows: List[Dict[str, Any]], count: int = 5,
                         min_spacing: int = 12) -> List[Dict[str, Any]]:
    """Choose well-spaced, high-confidence candidate frames; never call them verified."""
    ranked = []
    for row in rows:
        score, min_conf = _frame_score(row)
        if score >= 0:
            ranked.append((score, min_conf, int(row.get("frame", -1)), row))
    ranked.sort(key=lambda item: (-item[0], item[2]))
    selected = []
    for score, min_conf, frame, row in ranked:
        if frame < 1 or any(abs(frame - item["frame"]) < min_spacing for item in selected):
            continue
        selected.append({"frame": frame, "proposal_score": round(score, 4),
                         "minimum_detector_confidence": round(min_conf, 4),
                         "selection_status": "SUGGESTED_FOR_MANUAL_REVIEW"})
        if len(selected) >= max(1, count):
            break
    return sorted(selected, key=lambda item: item["frame"])


def prepare_review(video: Path, track_path: Path, output_dir: Path,
                   cv2_module=None, frame_count: int = 5) -> Dict[str, Any]:
    """Extract side-panel review stills and a separate editable proposal JSON."""
    if cv2_module is None:
        import cv2 as cv2_module
    video, track_path, output_dir = Path(video).resolve(), Path(track_path).resolve(), Path(output_dir).resolve()
    if not video.is_file() or not track_path.is_file():
        raise FileNotFoundError("Reference video or prediction track does not exist")
    raw_track = json.loads(track_path.read_text(encoding="utf-8-sig"))
    rows = sorted(raw_track.get("frames", []), key=lambda item: int(item.get("frame", -1)))
    if not rows:
        raise ValueError("The prediction track contains no frames")
    selected = select_review_frames(rows, frame_count)
    if not selected:
        raise ValueError("No usable hip/knee/ankle/foot proposal rows were found")

    output_dir.mkdir(parents=True, exist_ok=True)
    capture = cv2_module.VideoCapture(str(video))
    if not capture.isOpened():
        raise RuntimeError(f"OpenCV could not open reference video: {video}")
    width = int(capture.get(cv2_module.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2_module.CAP_PROP_FRAME_HEIGHT))
    frame_total = int(capture.get(cv2_module.CAP_PROP_FRAME_COUNT))
    fps = float(capture.get(cv2_module.CAP_PROP_FPS) or 0.0)
    track_by_frame = {int(row["frame"]): row for row in rows}
    review_rows = []
    try:
        for candidate in selected:
            frame = int(candidate["frame"])
            if frame > frame_total:
                continue
            capture.set(cv2_module.CAP_PROP_POS_FRAMES, frame - 1)
            ok, image = capture.read()
            if not ok:
                continue
            # DLC points are in the 640x720 side-panel coordinate system. The
            # source is a 1280x720 side-panel recording with the subject in the
            # left half; crop that panel instead of squeezing the whole frame.
            if width == 1280 and height == 720:
                image = image[:, :640].copy()
                image_transform = "crop_left_panel_x0_640_no_scale"
            elif width == 640 and height == 720:
                image_transform = "identity_640x720"
            else:
                raise ValueError(
                    f"Cannot safely map {width}x{height} video pixels to the track's "
                    "640x720 coordinates. Crop/declare the camera panel first; no resize is applied."
                )
            image_path = output_dir / f"frame_{frame:06d}_camera_A.png"
            if not cv2_module.imwrite(str(image_path), image):
                raise RuntimeError(f"Could not write review still: {image_path}")
            source_row = track_by_frame[frame]
            landmarks = {}
            for name in LANDMARKS:
                xy = source_row.get("landmarks_2d", {}).get(name)
                confidence = float(source_row.get("confidence", {}).get(name, 0.0))
                if not isinstance(xy, (list, tuple)) or len(xy) < 2:
                    landmarks[f"Leg_Reference_{name}"] = {
                        "visible": False, "state": "uncertain_missing_proposal",
                        "visibility_status": "UNOBSERVED",
                        "confidence": 0.0, "source": "missing_from_prediction_track"}
                    continue
                landmarks[f"Leg_Reference_{name}"] = {
                    "x": float(xy[0]), "y": float(xy[1]), "visible": True,
                    "state": "prediction_only", "confidence": confidence,
                    "visibility_status": "UNVERIFIED_PROPOSAL",
                    "source": "DeepLabCut_prediction_unverified"}
            review_rows.append({"frame": frame, "camera_A": {"landmarks": landmarks},
                                "prediction_row_status": source_row.get("status", "prediction"),
                                "candidate_score": candidate["proposal_score"]})
    finally:
        capture.release()
    if not review_rows:
        raise RuntimeError("No review stills could be extracted for the selected frames")

    payload = {
        "schema_version": 2,
        "status": "PREDICTIONS_ONLY_REVIEW_REQUIRED",
        "source_video": str(video), "source_video_sha256": sha256_file(video),
        "source_track": str(track_path), "source_track_sha256": sha256_file(track_path),
        "source_video_metadata": {"width": width, "height": height, "fps": fps,
                                  "frame_count": frame_total},
        "review_image_size": [640, 720], "review_image_transform": image_transform,
        "panel": "side / camera_A", "suggested_frames": selected,
        "identity": "UNVERIFIED", "identity_verified": False,
        "rig_armature": "", "rig_chain_bones": [],
        "frames": review_rows,
        "notes": ["All coordinates begin as detector predictions; none are confirmed.",
                  "A displayed proposal is not proof that the joint is visible to the eye.",
                  "Markers are shown without connecting lines until a physical rig-leg identity is approved.",
                  "Use Hide/Uncertain for any point that is not visibly identifiable in this image.",
                  "This review does not authorize 3D fitting or animation."],
    }
    review_path = output_dir / "landmark_review.json"
    review_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {"review_json": str(review_path), "samples_dir": str(output_dir),
            "selected_frames": [row["frame"] for row in review_rows],
            "video_sha256": payload["source_video_sha256"],
            "track_sha256": payload["source_track_sha256"],
            "metadata": payload["source_video_metadata"]}


def build_approved_track(review: Dict[str, Any], leg: str) -> Dict[str, Any]:
    """Build sparse evidence only from manually confirmed points.

    Partial chains are retained with explicit OCCLUDED/UNVERIFIED states; they
    are never converted into coordinates or counted as complete step evidence.
    """
    frames = []
    for row in sorted(review.get("frames", []), key=lambda item: int(item.get("frame", -1))):
        points = row.get("camera_A", {}).get("landmarks", {})
        names = {name: points.get(f"Leg_Reference_{name}", {}) for name in LANDMARKS}
        reviewed = {}
        for name, item in names.items():
            is_manual_visible = (item.get("visible") is True
                                 and item.get("state") == "manual_reviewed"
                                 and item.get("source") in {"native_review_click", "native_review_drag", "native_review_user_confirmed"}
                                 and all(k in item and math.isfinite(float(item[k])) for k in ("x", "y")))
            is_occluded = (item.get("visible") is False
                           and item.get("state") == "occluded")
            if not is_manual_visible and not is_occluded:
                item = {"visible": False, "state": "unverified",
                         "visibility_status": "UNVERIFIED", "source": "not_manually_reviewed"}
            reviewed[name] = item
        if not any(item.get("state") == "manual_reviewed" for item in reviewed.values()):
            continue
        coords = {name: [float(item["x"]), float(item["y"])]
                  for name, item in reviewed.items() if item.get("state") == "manual_reviewed"}
        states = {name: ("manually_reviewed" if item.get("state") == "manual_reviewed"
                         else "occluded" if item.get("state") == "occluded"
                         else "unverified") for name, item in reviewed.items()}
        frames.append({"frame": int(row["frame"]), "leg": f"Leg_{leg}",
                       "landmarks_2d": coords,
                       "confidence": {name: (1.0 if states[name] == "manually_reviewed" else 0.0)
                                      for name in LANDMARKS},
                       "source": "manual_blender_review", "status": "partial_manual_evidence",
                       "landmark_status": states})
    return {"schema_version": 1, "leg": f"Leg_{leg}", "fps": review.get("source_video_metadata", {}).get("fps"),
            "source_video": review.get("source_video"),
            "source_video_sha256": review.get("source_video_sha256"),
            "source_prediction_track": review.get("source_track"),
            "source_prediction_track_sha256": review.get("source_track_sha256"),
            "frames": frames}
