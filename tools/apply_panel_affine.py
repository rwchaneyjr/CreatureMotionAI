"""Apply saved detector-to-camera panel affine corrections."""
import argparse,json
from pathlib import Path

def main():
    p=argparse.ArgumentParser(); p.add_argument('--proposals',required=True); p.add_argument('--calibration',required=True); p.add_argument('--output',required=True); a=p.parse_args()
    data=json.loads(Path(a.proposals).read_text(encoding='utf-8')); cal=json.loads(Path(a.calibration).read_text(encoding='utf-8'))['cameras']
    for row in data.get('frames',[]):
        for cam in ('camera_A','camera_B'):
            c=cal.get(cam,{}); sx,sy,ox,oy=c.get('scale_x',1),c.get('scale_y',1),c.get('offset_x',0),c.get('offset_y',0)
            for item in row.get(cam,{}).get('landmarks',{}).values():
                item['x']=float(item['x'])*sx+ox; item['y']=float(item['y'])*sy+oy; item['panel_affine_applied']=True
    data['status']='panel_affine_corrected'; data['panel_affine_source']=str(Path(a.calibration).resolve())
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(data,indent=2),encoding='utf-8'); print(json.dumps({'output':str(out),'frames':len(data.get('frames',[]))}))
if __name__=='__main__': main()
