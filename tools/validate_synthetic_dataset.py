"""Validate synthetic two-camera labels without training or downloading weights."""
import argparse, json, math
from pathlib import Path

def main():
    p=argparse.ArgumentParser(); p.add_argument('--dataset',required=True); p.add_argument('--output',required=True); a=p.parse_args()
    rows=[json.loads(x) for x in (Path(a.dataset)/'labels.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
    issues=[]; stats={}
    for cam in ('camera_A','camera_B'):
        visible=occluded=out=bad=0; names=None
        for row in rows:
            pts=row['cameras'][cam]['joints_2d']; names=set(pts) if names is None else names
            if set(pts)!=names: issues.append({'sample':row['sample'],'camera':cam,'type':'joint_name_mismatch'})
            for name,v in pts.items():
                if len(v)!=4 or any(not isinstance(x,(int,float,bool)) for x in v): bad+=1; continue
                x,y,inside,vis=v
                if not all(math.isfinite(float(q)) for q in (x,y)): bad+=1
                if inside: visible+=int(bool(vis)); occluded+=int(not bool(vis))
                else: out+=1
        stats[cam]={'visible':visible,'occluded':occluded,'out_of_frame':out,'invalid_values':bad}
    report={'dataset':str(Path(a.dataset).resolve()),'samples':len(rows),'cameras':stats,'issues':issues,'pass':not issues and all(v['invalid_values']==0 and v['out_of_frame']==0 for v in stats.values()),'training_started':False,'next_gate':'approve label distribution before downloading detector weights'}
    Path(a.output).write_text(json.dumps(report,indent=2),encoding='utf-8'); print(json.dumps(report,indent=2))
if __name__=='__main__': main()
