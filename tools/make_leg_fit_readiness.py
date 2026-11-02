"""Summarize per-leg evidence before bounded 24-frame fitting."""
import argparse, json
from pathlib import Path

LEGS=("Leg_Front.L","Leg_Front.R","Leg_MidFront.L","Leg_MidFront.R","Leg_MidRear.L","Leg_MidRear.R","Leg_Rear.L","Leg_Rear.R")

def state(v):
    return v.get('state','uncertain') if isinstance(v,dict) else 'uncertain'

def main():
    p=argparse.ArgumentParser(); p.add_argument('--triangulation',required=True); p.add_argument('--output',required=True); a=p.parse_args()
    data=json.loads(Path(a.triangulation).read_text(encoding='utf-8'))
    frames=[]
    for row in data.get('frames',[]):
        joints=row.get('joints',{}); legs=[]
        for leg in LEGS:
            names=[f'{leg}_{n:02d}_{part}' for n in (1,2,3) for part in ('head','tail')]
            states=[state(joints.get(n)) for n in names]
            tri=sum(s=='triangulated' for s in states); temp=sum(s=='temporal_estimate' for s in states)
            # A chain is fit-eligible only when at least two joints are triangulated.
            eligible=tri>=2
            legs.append({'leg':leg,'triangulated_observations':tri,'temporal_observations':temp,'uncertain_observations':len(states)-tri-temp,'eligible':eligible,'action':'fit_bounded_offset' if eligible else 'hold_previous_valid_pose'})
        frames.append({'frame':row.get('frame'),'legs':legs,'eligible_legs':sum(x['eligible'] for x in legs)})
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)
    report={'status':'diagnostic','frame_count':len(frames),'frames':frames,'policy':'never_guess_hidden_or_ambiguous_leg'}
    out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'output':str(out),'frames':len(frames),'eligible_counts':[x['eligible_legs'] for x in frames]}))
if __name__=='__main__': main()
