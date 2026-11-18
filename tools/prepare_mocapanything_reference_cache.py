import os
import cv2

src = r"external/MocapAnything/poc_videos24/Balisk#walk24.mp4"
dst = r"external/MocapAnything/zoo/image/Balisk#Balisk-Move/y0"
os.makedirs(dst, exist_ok=True)
cap = cv2.VideoCapture(src)
for i in range(24):
    ok, frame = cap.read()
    if not ok:
        break
    cv2.imwrite(os.path.join(dst, f"{i:05d}.png"), frame)
cap.release()
print(dst)
