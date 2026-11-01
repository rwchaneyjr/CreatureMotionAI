import argparse
from pathlib import Path
import cv2

def main():
    p=argparse.ArgumentParser(); p.add_argument('--render-dir',required=True); p.add_argument('--output',required=True); p.add_argument('--frames',type=int,required=True); a=p.parse_args(); first=cv2.imread(str(Path(a.render_dir)/'blender_001.png')); h,w=first.shape[:2]; writer=cv2.VideoWriter(a.output,cv2.VideoWriter_fourcc(*'mp4v'),24,(w,h))
    for i in range(1,a.frames+1): writer.write(cv2.imread(str(Path(a.render_dir)/f'blender_{i:03d}.png')))
    writer.release(); print({'frames':a.frames,'output':a.output})
if __name__=='__main__': main()
