"""Run the synthetic-trained DINO coordinate head as low-confidence proposals."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
from PIL import Image
from torch import nn


class Head(nn.Module):
    def __init__(self, channels: int, joints: int):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(channels, 512), nn.GELU(), nn.Linear(512, joints * 2), nn.Sigmoid())

    def forward(self, x):
        return self.net(x)


def read_frames(path: Path, stride: int):
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open {path}")
    index = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if index % stride == 0:
            yield index + 1, Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        index += 1
    cap.release()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--model-cache", type=Path, default=Path("models"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stride", type=int, default=6)
    parser.add_argument("--proposal-confidence", type=float, default=0.25)
    args = parser.parse_args()
    import torch
    from transformers import AutoImageProcessor, AutoModel
    checkpoint = torch.load(args.weights, map_location="cpu")
    joints = checkpoint["joints"]
    processor = AutoImageProcessor.from_pretrained("facebook/dinov2-base", cache_dir=args.model_cache, local_files_only=True)
    backbone = AutoModel.from_pretrained("facebook/dinov2-base", cache_dir=args.model_cache, local_files_only=True).eval()
    head = Head(backbone.config.hidden_size, len(joints))
    head.load_state_dict(checkpoint["state_dict"])
    head.eval()
    frames = []
    for number, split in read_frames(args.video, args.stride):
        half = split.width // 2
        views = {"camera_A": split.crop((0, 0, half, split.height)), "camera_B": split.crop((half, 0, split.width, split.height))}
        row = {"frame": number}
        for camera, image in views.items():
            with torch.no_grad():
                features = backbone(**processor(images=image, return_tensors="pt")).last_hidden_state[:, 1:, :].mean(1)
                points = head(features)[0].reshape(len(joints), 2).tolist()
            row[camera] = {"landmarks": {name: {"x": p[0] * half, "y": p[1] * split.height, "visible": True, "confidence": args.proposal_confidence, "state": "proposal"} for name, p in zip(joints, points)}}
        frames.append(row)
    result = {"source_video": str(args.video), "frames": frames, "joint_names": joints, "status": "low_confidence_proposals", "real_video_review_required": True, "note": "These are synthetic-trained proposals. They are intentionally below the triangulation confidence threshold by default."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "frames": len(frames), "joints": len(joints), "confidence": args.proposal_confidence}, indent=2))


if __name__ == "__main__":
    main()
