import cv2
from pathlib import Path
import numpy as np

video = Path(r'C:\Users\rober\Downloads\2VIEWSBALISK SYNCWALK.mp4')
out = Path(r'C:\Users\rober\CreatureMotionAI\data\generated\e2e_balisk_test\builder\bending_diagnosis\identity_labels')
out.mkdir(parents=True, exist_ok=True)
cap = cv2.VideoCapture(str(video))
frames = [1, 60, 120, 180]
tiles = []
for f in frames:
    cap.set(cv2.CAP_PROP_POS_FRAMES, f - 1)
    ok, im = cap.read()
    if not ok:
        continue
    h, w = im.shape[:2]
    side = cv2.resize(im[:, :w // 2].copy(), (640, 360))
    cv2.rectangle(side, (0, 0), (639, 42), (0, 0, 0), -1)
    cv2.putText(side, f'Reference frame {f} - LEG IDENTITY UNVERIFIED', (12, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.72, (0, 220, 255), 2, cv2.LINE_AA)
    tiles.append(side)
cap.release()
if tiles:
    while len(tiles) < 4:
        tiles.append(np.zeros_like(tiles[0]))
    sheet = np.vstack([np.hstack(tiles[:2]), np.hstack(tiles[2:4])])
    cv2.imwrite(str(out / 'reference_leg_identity_unverified.png'), sheet)
print(out / 'reference_leg_identity_unverified.png')
