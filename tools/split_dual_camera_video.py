"""Split and validate a synchronized two-panel creature reference video.

The expected input is one video containing two views of the same take:
left = side view, right = approximately 90-degree front/three-quarter view.
No pose fitting or triangulation is performed here; this is an input-quality gate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2


def _writer(path: Path, fps: float, size: tuple[int, int]) -> cv2.VideoWriter:
    path.parent.mkdir(parents=True, exist_ok=True)
    for codec in ("mp4v", "avc1"):
        writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*codec), fps, size)
        if writer.isOpened():
            return writer
        writer.release()
    raise RuntimeError(f"Could not open an MP4 writer for {path}")


def split_video(input_path: Path, output_dir: Path, expected_angle: float = 90.0) -> dict:
    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open input video: {input_path}")
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if width < 4 or height < 2:
        cap.release()
        raise ValueError("Input video has invalid dimensions")
    if width % 2:
        cap.release()
        raise ValueError(f"Split-screen width must be even, got {width}")
    panel_width = width // 2
    output_dir.mkdir(parents=True, exist_ok=True)
    left_path = output_dir / "camera_A_side.mp4"
    right_path = output_dir / "camera_B_front.mp4"
    left_writer = _writer(left_path, fps or 30.0, (panel_width, height))
    right_writer = _writer(right_path, fps or 30.0, (panel_width, height))
    read_count = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            left_writer.write(frame[:, :panel_width])
            right_writer.write(frame[:, panel_width:])
            read_count += 1
    finally:
        cap.release()
        left_writer.release()
        right_writer.release()

    report = {
        "input": str(input_path),
        "output_dir": str(output_dir),
        "fps": fps,
        "width": width,
        "height": height,
        "panel_width": panel_width,
        "metadata_frame_count": frame_count,
        "decoded_frame_count": read_count,
        "synchronized_frame_count": read_count,
        "expected_view_separation_degrees": expected_angle,
        "left_view": "camera_A_side",
        "right_view": "camera_B_front",
        "valid": bool(read_count > 0 and (frame_count == 0 or abs(frame_count - read_count) <= 1)),
        "warnings": [],
    }
    if not fps:
        report["warnings"].append("Input FPS was unavailable; writers used 30 FPS.")
    if frame_count and abs(frame_count - read_count) > 1:
        report["warnings"].append("Decoded frame count differs from container metadata.")
    if read_count == 0:
        report["warnings"].append("No frames were decoded.")
    report_path = output_dir / "dual_camera_video_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--view-separation", type=float, default=90.0)
    args = parser.parse_args()
    report = split_video(args.input, args.output_dir, args.view_separation)
    print(json.dumps(report, indent=2))
    if not report["valid"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
