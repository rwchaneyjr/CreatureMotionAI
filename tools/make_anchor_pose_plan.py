"""Select sparse anchor frames for bounded pose fitting."""
import argparse,json
from pathlib import Path

def main():
    p=argparse.ArgumentParser(); p.add_argument('triangulation',type=Path); p.add_argument('--output',required=True,type=Path); p.add_argument('--frames',default='1,6,12,18,24'); a=p.parse_args()
    data=json.loads(a.triangulation.read_text(encoding='utf-8')); wanted={int(x) for x in a.frames.split(',')}; rows=[]
    for row in data.get('frames',[]):
        f=int(row.get('frame',0))
        if f in wanted:
            joints=row.get('joints',{}); rows.append({'frame':f,'triangulated':sum(v.get('state')=='triangulated' for v in joints.values()),'temporal_estimate':sum(v.get('state')=='temporal_estimate' for v in joints.values()),'uncertain':sum(v.get('state') not in {'triangulated','temporal_estimate'} for v in joints.values()),'status':'pending_bounded_fit'})
    result={'source':str(a.triangulation),'anchors':rows,'anchor_count':len(rows),'status':'pending_bounded_fit','note':'No bone rotations have been written.'}
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps({'output':str(a.output),'anchors':len(rows)}))
if __name__=='__main__': main()
