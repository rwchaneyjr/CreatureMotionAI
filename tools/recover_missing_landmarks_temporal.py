"""Carry short landmark gaps forward as uncertain estimates, never as visible labels."""
import argparse,json
from pathlib import Path

def main():
    p=argparse.ArgumentParser(); p.add_argument('input',type=Path); p.add_argument('--output',required=True,type=Path); p.add_argument('--max-gap',type=int,default=6); a=p.parse_args()
    data=json.loads(a.input.read_text(encoding='utf-8')); frames=data.get('frames',[]); last={}; last_frame={}; recovered=0
    for row in frames:
        frame=int(row.get('frame',0))
        for name,item in row.get('joints',{}).items():
            if item.get('state')=='triangulated': last[name]=item.copy(); last_frame[name]=frame; continue
            if name in last and frame-last_frame[name] <= a.max_gap:
                row['joints'][name]={**last[name], 'state':'temporal_estimate','source_frame':last_frame[name], 'confidence':float(last[name].get('confidence',0))*0.5}
                recovered+=1
    result={**data,'frames':frames,'status':'provisional_temporal_recovery','recovered_points':recovered,'note':'Temporal estimates are uncertain and must not be exported as final labels.'}
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps({'output':str(a.output),'recovered_points':recovered}))
if __name__=='__main__': main()
