import argparse
from pathlib import Path
import cv2

def main():
    p=argparse.ArgumentParser(); p.add_argument('--video',required=True); p.add_argument('--render-dir',required=True); p.add_argument('--output',required=True); a=p.parse_args()
    cap=cv2.VideoCapture(a.video); fps=cap.get(cv2.CAP_PROP_FPS) or 24; first=cv2.imread(str(Path(a.render_dir)/'blender_001.png'))
    if first is None: raise RuntimeError('No Blender renders found')
    h,w=first.shape[:2]; writer=cv2.VideoWriter(a.output,cv2.VideoWriter_fourcc(*'mp4v'),fps,(w*2,h))
    i=1
    while True:
        ok,ref=cap.read()
        if not ok: break
        render=cv2.imread(str(Path(a.render_dir)/f'blender_{i:03d}.png'))
        if render is None: break
        ref=cv2.resize(ref,(w,h)); frame=cv2.hconcat([ref,render]); cv2.putText(frame,'MP4',(20,35),0,.9,(0,255,255),2); cv2.putText(frame,'Blender corrected',(w+20,35),0,.9,(0,255,255),2); writer.write(frame); i+=1
    cap.release(); writer.release(); print({'frames':i-1,'output':a.output})
if __name__=='__main__': main()
