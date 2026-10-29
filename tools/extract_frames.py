"""Extract MP4 frames and metadata without changing the source video."""
import argparse
import json
from pathlib import Path

import cv2


def extract(video: Path, output: Path, start: int = 0, end: int | None = None) -> dict:
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise RuntimeError(f"Could not open video: {video}")
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
    total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    if start < 0 or (end is not None and end <= start):
        raise ValueError("Frame range must satisfy 0 <= start < end")
    end = total if end is None else min(end, total)
    if start >= total:
        raise ValueError(f"Start frame {start} is outside video ({total} frames)")
    output.mkdir(parents=True, exist_ok=True)
    capture.set(cv2.CAP_PROP_POS_FRAMES, start)
    written = []
    for index in range(start, end):
        ok, frame = capture.read()
        if not ok:
            break
        path = output / f"frame_{index + 1:06d}.png"
        if not cv2.imwrite(str(path), frame):
            raise RuntimeError(f"Could not write {path}")
        written.append(path.name)
        if len(written) == 1 or len(written) % 10 == 0 or index + 1 == end:
            print(f"Extracted {len(written)}/{end - start} frames", flush=True)
    capture.release()
    metadata = {
        "video": str(video), "fps": fps, "frame_count": total,
        "width": width, "height": height, "start_frame": start,
        "end_frame_exclusive": end, "frames_written": len(written),
        "files": written,
    }
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int)
    args = parser.parse_args()
    result = extract(args.video, args.output, args.start, args.end)
    print(json.dumps({k: result[k] for k in ("fps", "frame_count", "width", "height", "frames_written")}, indent=2))


if __name__ == "__main__":
    main()

