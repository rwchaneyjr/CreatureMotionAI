"""Synchronized Rear.L reference/render comparison with explicit presentation transform.

The Blender panel is mirrored because its +X camera sees the original .L side
while the reference creature faces in the opposite screen direction. The
aligned panel also translates the image vertically; this affects pixels only,
never the rig, pose, or saved .blend.
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def panel(image, label):
    image = cv2.resize(image, (640, 360))
    image = image[:, :640]
    cv2.rectangle(image, (0, 0), (640, 32), (25, 25, 25), -1)
    cv2.putText(image, label, (9, 23), cv2.FONT_HERSHEY_SIMPLEX,
                0.56, (255, 255, 255), 1, cv2.LINE_AA)
    return image


def main():
    parser = argparse.ArgumentParser()
    for name in ("video", "renders", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(args.video))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot read reference {args.video}")
    writer = cv2.VideoWriter(str(args.output / "rearL_hybrid_32f_comparison.mp4"),
                             cv2.VideoWriter_fourcc(*"mp4v"), 24, (1920, 360))
    if not writer.isOpened():
        raise RuntimeError("Cannot encode comparison video")
    keyframes = (1, 12, 18, 24, 30, 32)
    key_images = []
    for frame in range(1, 33):
        ok, reference = cap.read()
        if not ok:
            raise RuntimeError(f"Reference ends before frame {frame}")
        render_path = args.renders / f"frame_{frame:02}.png"
        render = cv2.imread(str(render_path))
        if render is None:
            raise RuntimeError(f"Missing Blender render {render_path}")
        if reference.shape[:2] != (720, 1280):
            reference = cv2.resize(reference, (1280, 720))
        reference = cv2.resize(reference[:, :720], (640, 360))
        render = cv2.resize(render, (1280, 720))
        mirrored = cv2.flip(render, 1)[:, :720]
        raw = cv2.resize(mirrored, (640, 360))
        # Frame-1 framing offset: Blender creature is about 90 source pixels
        # lower. This is a documented image-space calibration diagnostic.
        shifted = cv2.warpAffine(mirrored, np.float32([[1, 0, 0], [0, 1, -90]]),
                                 (720, 720), borderValue=(205, 205, 205))
        aligned = cv2.resize(shifted, (640, 360))
        result = np.hstack((
            panel(reference, f"Reference  /  frame {frame}"),
            panel(raw, "Blender original camera / mirrored"),
            panel(aligned, "Blender + 90px vertical alignment"),
        ))
        writer.write(result)
        if frame in keyframes:
            cv2.imwrite(str(args.output / f"comparison_{frame:02}.png"), result)
            key_images.append(result)
    writer.release()
    cap.release()
    cv2.imwrite(str(args.output / "keyframes_montage.png"), np.vstack(key_images))
    report = {"source_video": str(args.video), "frame_count": 32, "fps": 24,
              "render_mirror": "horizontal to show original .L side facing video direction",
              "presentation_translation_pixels_at_1280x720": [0, -90],
              "translation_applied_to_original_blend": False,
              "reference_frames_are_actual_video_frames": True,
              "visual_verdict": "PENDING_REVIEW"}
    (args.output / "comparison_metadata.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
