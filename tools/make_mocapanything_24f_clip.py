import cv2
import os

src = r"external/MocapAnything/poc_videos2/Balisk#walk.mp4"
out_dir = r"external/MocapAnything/poc_videos24"
os.makedirs(out_dir, exist_ok=True)
out = os.path.join(out_dir, "Balisk#walk24.mp4")
cap = cv2.VideoCapture(src)
fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
writer = cv2.VideoWriter(out, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
for _ in range(24):
    ok, frame = cap.read()
    if not ok:
        break
    writer.write(frame)
cap.release()
writer.release()
print(out)
