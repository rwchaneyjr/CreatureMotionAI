"""Map the original rig's projected joints into single-camera video bboxes as editable predictions."""
import argparse, json
from pathlib import Path

def main():
    p=argparse.ArgumentParser(); p.add_argument('--candidates',required=True); p.add_argument('--motion',required=True); p.add_argument('--synthetic',required=True); p.add_argument('--output',required=True); p.add_argument('--frames',default='2,5,9,22,24'); a=p.parse_args(); candidates=json.loads(Path(a.candidates).read_text()); motion=json.loads(Path(a.motion).read_text()); synth=json.loads(Path(a.synthetic).read_text()); selected={int(x) for x in a.frames.split(',')}; synth_by={int(x['frame']):x for x in synth['frames']}; motion_by={int(x['frame'])+1:x for x in motion['frames']}; rows=[]
    for row in candidates['frames'][:24]:
        f=int(row['frame']); out=dict(row); out['camera_A']={'landmarks':dict(row.get('camera_A',{}).get('landmarks',{}))}; s=synth_by.get(f); m=motion_by.get(f)
        if f in selected and s and m:
            rx0=m['landmarks']['motion_left'][0]*1280; rx1=m['landmarks']['motion_right'][0]*1280; ry0=m['landmarks']['motion_top'][1]*720; ry1=m['landmarks']['motion_bottom'][1]*720
            pts=[]
            for name,item in s['camera_A']['landmarks'].items():
                if not any(k in name for k in ('_hip','_knee','_ankle')) and name not in ('body_center','head','tail_base','tail_tip'): continue
                if item.get('x') is None: continue
                pts.append((item['x'],item['y']))
            sx0=min(x for x,y in pts); sx1=max(x for x,y in pts); sy0=min(y for x,y in pts); sy1=max(y for x,y in pts)
            for name,item in s['camera_A']['landmarks'].items():
                if not any(k in name for k in ('_hip','_knee','_ankle')) and name not in ('body_center','head','tail_base','tail_tip'): continue
                x=rx0+(item['x']-sx0)/max(sx1-sx0,1)*(rx1-rx0); y=ry0+(item['y']-sy0)/max(sy1-sy0,1)*(ry1-ry0)
                out['camera_A']['landmarks'][name]={'x':x,'y':y,'visible':True,'confidence':0.35,'state':'model_prediction','source':'original_rig_projection_mapped_to_video_bbox'}
        rows.append(out)
    result={'status':'model_predictions_for_native_review','frames':rows,'selected_review_frames':sorted(selected),'note':'MODEL PREDICTION markers are guides only. They are not observed landmarks and must be corrected and explicitly reviewed before fitting.'}; Path(a.output).write_text(json.dumps(result,indent=2)); print(json.dumps({'output':a.output,'frames':len(rows),'selected':sorted(selected)}))
if __name__=='__main__': main()
