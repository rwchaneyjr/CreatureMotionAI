"""Coordinate-descent search for per-station eight-leg gait parameters."""
import argparse, json, subprocess
from pathlib import Path
import cv2, numpy as np

def score(video, render_dir):
    cap=cv2.VideoCapture(video); vals=[]
    for f in (1,12,24):
        cap.set(cv2.CAP_PROP_POS_FRAMES,f-1); ok,ref=cap.read(); img=cv2.imread(str(Path(render_dir)/f'blender_{f:03d}.png'))
        if not ok or img is None: continue
        ref=cv2.resize(ref,(img.shape[1],img.shape[0])); _,a=cv2.threshold(cv2.cvtColor(ref,cv2.COLOR_BGR2GRAY),150,255,cv2.THRESH_BINARY_INV); _,b=cv2.threshold(cv2.cvtColor(img,cv2.COLOR_BGR2GRAY),20,255,cv2.THRESH_BINARY); vals.append(np.logical_and(a>0,b>0).sum()/max(np.logical_or(a>0,b>0).sum(),1))
    cap.release(); return float(np.mean(vals)) if vals else 0.0

def main():
    p=argparse.ArgumentParser(); [p.add_argument(x,required=True) for x in ('--model','--motion','--video','--blender','--output','--report','--work')]; a=p.parse_args(); work=Path(a.work); work.mkdir(parents=True,exist_ok=True); phases=[0.0]*4; strides=[1.0]*4; best=0.0
    for station in range(4):
      for kind, values in [('phase',(-0.18,0.0,0.18)),('stride',(0.8,1.0,1.2))]:
       local=(phases if kind=='phase' else strides)[station]
       for value in values:
        trial_phases=phases[:]; trial_strides=strides[:]
        (trial_phases if kind=='phase' else trial_strides)[station]=value
        out=work/f'trial_{station}_{kind}_{str(value).replace("-","m")}.blend'; rep=work/f'{out.stem}.json'
        cmd=[a.blender,'--background','--python',str(Path(__file__).with_name('solve_eight_leg_video.py')),'--','--model',a.model,'--motion',a.motion,'--output',str(out),'--report',str(rep),'--station-phase='+','.join(map(str,trial_phases)),'--station-stride='+','.join(map(str,trial_strides))]
        subprocess.run(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True); value_score=score(a.video,out.parent/'eight_leg_render')
        if value_score>=best: best=value_score; (phases if kind=='phase' else strides)[station]=value
    final=work/'best.blend'; subprocess.run([a.blender,'--background','--python',str(Path(__file__).with_name('solve_eight_leg_video.py')),'--','--model',a.model,'--motion',a.motion,'--output',str(final),'--report',str(work/'best.json'),'--station-phase='+','.join(map(str,phases)),'--station-stride='+','.join(map(str,strides))],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True); Path(final).replace(a.output); result={'best_mean_iou':best,'station_phase':phases,'station_stride':strides,'output':a.output}; Path(a.report).write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps(result))
if __name__=='__main__': main()
