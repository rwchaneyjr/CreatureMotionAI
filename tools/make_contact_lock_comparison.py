"""Create same-camera original-vs-contact-lock video and review sheet."""
from pathlib import Path
import cv2
import numpy as np

root = Path(__file__).resolve().parents[1]
base = root / "data/generated/balisk_camera_fullbody_walk_02"
out = base / "contact_lock_v1"
source = cv2.VideoCapture(str(base / "walk_5sec.mp4"))
if not source.isOpened():
    raise RuntimeError("Cannot open baseline preview")
fps = source.get(cv2.CAP_PROP_FPS) or 24
writer = cv2.VideoWriter(str(out / "original_vs_contact_locked_5sec.mp4"),
                         cv2.VideoWriter_fourcc(*"mp4v"), fps, (2560, 720))
if not writer.isOpened():
    raise RuntimeError("Cannot create comparison MP4")
sheet_rows = []
key_frames = {1, 30, 60, 90, 120}
for i in range(1, 121):
    ok, original = source.read()
    candidate = cv2.imread(str(out / f"candidate_frames/frame_{i:04d}.png"))
    if not ok or candidate is None:
        raise RuntimeError(f"Missing frame {i}: source={ok}, candidate={candidate is not None}")
    candidate = cv2.resize(candidate, (1280, 720), interpolation=cv2.INTER_CUBIC)
    for image, label in ((original, "Original loop"), (candidate, "Contact locked")):
        cv2.rectangle(image, (0, 0), (260, 42), (20, 20, 20), -1)
        cv2.putText(image, label, (16, 29), cv2.FONT_HERSHEY_SIMPLEX, 0.75,
                    (255, 255, 255), 2, cv2.LINE_AA)
    writer.write(np.hstack((original, candidate)))
    if i in key_frames:
        small_a = cv2.resize(original, (640, 360), interpolation=cv2.INTER_AREA)
        small_b = cv2.resize(candidate, (640, 360), interpolation=cv2.INTER_AREA)
        sheet_rows.append(np.hstack((small_a, small_b)))
source.release()
writer.release()
cv2.imwrite(str(out / "comparison_keyframes.png"), np.vstack(sheet_rows))
print(f"VIDEO {out / 'original_vs_contact_locked_5sec.mp4'}")
print(f"KEYFRAMES {out / 'comparison_keyframes.png'}")
