"""Create a DeepLabCut project for Creature Motion AI."""
import argparse
import json
from pathlib import Path

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
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--user", default="CreatureMotionAI")
    args = parser.parse_args()
    if not args.video.is_file():
        raise FileNotFoundError(args.video)
    args.output.mkdir(parents=True, exist_ok=True)
    import deeplabcut
    config_path = deeplabcut.create_new_project(
        args.user, "CreatureMotionAI", [str(args.video)],
        working_directory=str(args.output), copy_videos=False,
    )
    config = Path(config_path)
    landmark_path = config.parent / "creature_motion_ai_landmarks.json"
    landmark_path.write_text(json.dumps({"bodyparts": LANDMARKS}, indent=2), encoding="utf-8")
    print(json.dumps({"config": str(config), "landmarks": str(landmark_path), "count": len(LANDMARKS)}, indent=2))


if __name__ == "__main__":
    main()

