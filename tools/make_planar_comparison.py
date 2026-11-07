import argparse, cv2, json
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('--video', required=True)
ap.add_argument('--render-dir', required=True)
ap.add_argument('--output', required=True)
ap.add_argument('--report', required=True)
a = ap.parse_args()
cap = cv2.VideoCapture(a.video)
fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
frames = []
for i in range(24):
    ok, im = cap.read()
    if not ok:
        break
    r = cv2.imread(str(Path(a.render_dir) / f'frame_{i+1:03d}.png'))
    if r is None:
        continue
    im = cv2.resize(im, (640, 360)); r = cv2.resize(r, (640, 360))
    cv2.putText(im, 'REFERENCE SIDE VIEW', (16, 30), cv2.FONT_HERSHEY_SIMPLEX, .7, (255,255,255), 2)
    cv2.putText(r, 'PLANAR LEG_REAR.L TEST', (16, 30), cv2.FONT_HERSHEY_SIMPLEX, .7, (255,255,255), 2)
    frames.append(cv2.hconcat([im, r]))
if not frames:
    raise RuntimeError('No comparison frames produced')
out = Path(a.output); out.parent.mkdir(parents=True, exist_ok=True)
writer = cv2.VideoWriter(str(out), cv2.VideoWriter_fourcc(*'mp4v'), fps, (1280, 360))
for f in frames:
    writer.write(f)
writer.release(); cap.release()
Path(a.report).write_text(json.dumps({'status':'CREATED','frames':len(frames),'fps':fps,'output':str(out.resolve())}, indent=2), encoding='utf-8')
print(json.dumps({'frames':len(frames),'output':str(out.resolve())}))
