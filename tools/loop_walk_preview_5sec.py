import cv2

src = r"data/generated/Balisk_Usable_Walk_24f.mp4"
out = r"data/generated/Balisk_Usable_Walk_5sec.mp4"
cap = cv2.VideoCapture(src)
frames = []
fps = cap.get(cv2.CAP_PROP_FPS) or 24
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
while True:
    ok, image = cap.read()
    if not ok:
        break
    frames.append(image)
cap.release()
if not frames:
    raise RuntimeError("No frames decoded from source MP4")
writer = cv2.VideoWriter(out, cv2.VideoWriter_fourcc(*"mp4v"), 24, (width, height))
for i in range(120):
    writer.write(frames[i % len(frames)])
writer.release()
print(out, len(frames), "source frames ->", 120, "output frames")
