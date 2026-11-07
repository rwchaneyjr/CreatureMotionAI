"""Export DLC PyTorch H5 predictions to the CMAI confidence-scored format."""
import argparse, json
from pathlib import Path
import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--h5", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--leg", default="Leg_Rear.L")
    args = ap.parse_args()
    df = pd.read_hdf(args.h5)
    scorer = str(df.columns[0][0])
    bodyparts = ["hip", "knee", "ankle", "foot"]
    frames = []
    low = []
    for i, row in df.iterrows():
        landmarks, confidence = {}, {}
        for bp in bodyparts:
            x = float(row[(scorer, bp, "x")]); y = float(row[(scorer, bp, "y")])
            c = float(row[(scorer, bp, "likelihood")])
            landmarks[bp] = [x, y]
            confidence[bp] = c
            if c < 0.6:
                low.append({"frame": i + 1, "landmark": bp, "confidence": c})
        frames.append({"frame": i + 1, "leg": args.leg, "landmarks_2d": landmarks,
                       "confidence": confidence, "source": "DeepLabCut",
                       "status": "prediction"})
    out = Path(args.output); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"leg": args.leg, "fps": 24, "frames": frames}, indent=2), encoding="utf-8")
    report = {
        "status": "TRACKED_2D_ONLY",
        "source": str(Path(args.h5).resolve()),
        "scorer": scorer,
        "frames": len(frames),
        "landmarks_per_frame": len(bodyparts),
        "low_confidence_threshold": 0.6,
        "low_confidence_count": len(low),
        "low_confidence_examples": low[:100],
        "leg_identity": args.leg,
        "metric_3d_reconstruction": "NOT_ESTABLISHED",
        "action_generated": False,
    }
    Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
