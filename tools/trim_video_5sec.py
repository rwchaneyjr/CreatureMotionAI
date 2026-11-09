import sys, cv2

src, dst = sys.argv[1], sys.argv[2]
cap = cv2.VideoCapture(src)
fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
limit = min(int(cap.get(cv2.CAP_PROP_FRAME_COUNT)), round(fps * 5))
out = cv2.VideoWriter(dst, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
count = 0
while count < limit:
    ok, frame = cap.read()
    if not ok: break
    out.write(frame); count += 1
out.release(); cap.release()
print(dst, count, fps, w, h)
