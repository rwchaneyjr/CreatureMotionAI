"""Apply the Creature Motion AI landmark names to a DeepLabCut config."""
import argparse
from pathlib import Path

import yaml

LANDMARKS = [
    "head", "neck", "shoulder_center", "spine_center", "hip_center",
    "tail_base", "tail_middle", "tail_tip",
    "front_left_shoulder", "front_left_elbow", "front_left_wrist", "front_left_foot",
    "front_right_shoulder", "front_right_elbow", "front_right_wrist", "front_right_foot",
    "rear_left_hip", "rear_left_knee", "rear_left_ankle", "rear_left_foot",
    "rear_right_hip", "rear_right_knee", "rear_right_ankle", "rear_right_foot",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    config["bodyparts"] = LANDMARKS
    config["skeleton"] = []
    args.config.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    print(f"Applied {len(LANDMARKS)} landmarks to {args.config}")


if __name__ == "__main__":
    main()

