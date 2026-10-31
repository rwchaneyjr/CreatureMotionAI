"""Render-and-compare search over procedural gait parameters."""
import argparse, json, subprocess
from pathlib import Path
import cv2, numpy as np

def score(video, render_dir):
    cap=cv2.VideoCapture(video); vals=[]
    for f in (1,12,24):
        cap.set(cv2.CAP_PROP_POS_FRAMES,f-1); ok,ref=cap.read(); render=cv2.imread(str(Path(render_dir)/f'blender_{f:03d}.png'))
        if not ok or render is None: continue
        ref=cv2.resize(ref,(render.shape[1],render.shape[0])); rg=cv2.cvtColor(ref,cv2.COLOR_BGR2GRAY); bg=cv2.cvtColor(render,cv2.COLOR_BGR2GRAY)
        _,rm=cv2.threshold(rg,150,255,cv2.THRESH_BINARY_INV); _,bm=cv2.threshold(bg,20,255,cv2.THRESH_BINARY)
        vals.append(float(np.logical_and(rm>0,bm>0).sum()/max(np.logical_or(rm>0,bm>0).sum(),1)))
    cap.release(); return float(np.mean(vals)) if vals else 0.0

def main():
    p=argparse.ArgumentParser(); p.add_argument('--model',required=True); p.add_argument('--motion',required=True); p.add_argument('--video',required=True); p.add_argument('--blender',required=True); p.add_argument('--output',required=True); p.add_argument('--report',required=True); p.add_argument('--work',required=True); a=p.parse_args(); work=Path(a.work); work.mkdir(parents=True,exist_ok=True); best=(-1,None)
    for stride in (0.07,0.10,0.14):
      for lift in (0.04,0.07,0.11):
       for phase in (0.40,0.55,0.70):
        out=work/f'candidate_{stride}_{lift}_{phase}.blend'; report=work/f'{out.stem}.json'; render=out.parent/'eight_leg_render'
        cmd=[a.blender,'--background','--python',str(Path(__file__).with_name('solve_eight_leg_video.py')),'--','--model',a.model,'--motion',a.motion,'--output',str(out),'--report',str(report),'--stride',str(stride),'--lift',str(lift),'--phase-offset',str(phase)]
        subprocess.run(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
        value=score(a.video,render)
        if value>best[0]: best=(value,(stride,lift,phase,str(out)))
    stride,lift,phase,candidate=best[1]; Path(a.output).parent.mkdir(parents=True,exist_ok=True); Path(candidate).replace(a.output)
    result={'best_mean_iou':best[0],'stride':stride,'lift':lift,'phase_offset':phase,'output':a.output}; Path(a.report).write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps(result))
if __name__=='__main__': main()
