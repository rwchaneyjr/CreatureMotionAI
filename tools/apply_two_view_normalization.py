"""Apply provisional panel ground/scale normalization to landmark observations."""
import argparse,json
from pathlib import Path

def main():
    p=argparse.ArgumentParser(); p.add_argument('observations',type=Path); p.add_argument('normalization',type=Path); p.add_argument('--output',required=True,type=Path); a=p.parse_args()
    data=json.loads(a.observations.read_text(encoding='utf-8')); norm=json.loads(a.normalization.read_text(encoding='utf-8'))['normalization']; gs=norm['median_side_ground_row']; gf=norm['median_front_ground_row']; scale=norm['height_scale_front_to_side']; panel_w=640.0
    rows=[]
    for row in data.get('frames',[]):
        out={k:dict(v) for k,v in row.items() if k not in ('camera_A','camera_B')}
        for key,src in (('camera_A','camera_A'),('camera_B','camera_B')):
            cam=row.get(src,{})
            lms={}
            for name,item in cam.get('landmarks',{}).items():
                n=dict(item)
                if key=='camera_B' and 'y' in n:
                    n['y']=gf-(float(n['y'])-gf)*scale+gs-gs
                    n['normalization']='ground_scale_only'
                lms[name]=n
            out[key]={'landmarks':lms}
        rows.append(out)
    result={**data,'frames':rows,'status':'provisional_two_view_normalized','normalization_source':str(a.normalization),'note':'Front-panel vertical scale/ground normalization is provisional and must be rechecked against Blender renders.'}
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps({'output':str(a.output),'frames':len(rows),'scale':scale,'ground_side':gs,'ground_front':gf}))
if __name__=='__main__': main()
