"""Combine two-view landmark evidence and pose safety into a 24-frame leg report."""
import argparse, json
from pathlib import Path

LEGS=("Leg_Front.L","Leg_Front.R","Leg_MidFront.L","Leg_MidFront.R","Leg_MidRear.L","Leg_MidRear.R","Leg_Rear.L","Leg_Rear.R")

def main():
    p=argparse.ArgumentParser(); p.add_argument('--triangulation',required=True); p.add_argument('--identity-map',required=True); p.add_argument('--collision',required=True); p.add_argument('--output',required=True); a=p.parse_args()
    tri=json.loads(Path(a.triangulation).read_text(encoding='utf-8')); identities=json.loads(Path(a.identity_map).read_text(encoding='utf-8')); collision=json.loads(Path(a.collision).read_text(encoding='utf-8'))
    collision_by={int(x['frame']):x for x in collision.get('frames',[])}
    frames=[]; totals={leg:{'frames':0,'observed':0,'uncertain':0,'confidence_sum':0.0} for leg in LEGS}
    for row in tri.get('frames',[])[:24]:
        frame_no=int(row.get('frame',len(frames)+1)); joints=row.get('joints',{}); out=[]
        for leg in LEGS:
            names=[f'{leg}_{n:02d}_{part}' for n in (1,2,3) for part in ('head','tail')]
            obs=[joints.get(n,{}) for n in names]; good=[x for x in obs if x.get('state') in ('triangulated','temporal_estimate')]
            conf=sum(float(x.get('confidence',0.0)) for x in good)/max(len(good),1)
            state='tracked' if sum(x.get('state')=='triangulated' for x in obs)>=2 else 'uncertain'
            totals[leg]['frames']+=1; totals[leg]['observed']+=int(state=='tracked'); totals[leg]['uncertain']+=int(state!='tracked'); totals[leg]['confidence_sum']+=conf
            out.append({'leg':leg,'state':state,'observed_landmarks':len(good),'confidence':round(conf,4),'policy':'fit' if state=='tracked' else 'hold_previous_valid_pose'})
        c=collision_by.get(frame_no,{})
        frames.append({'frame':frame_no,'legs':out,'physical_valid':bool(c.get('accepted',False)),'collision_failures':len(c.get('failures',[]))})
    summary=[]
    for leg,v in totals.items(): summary.append({'leg':leg,'tracked_fraction':round(v['observed']/max(v['frames'],1),4),'uncertain_fraction':round(v['uncertain']/max(v['frames'],1),4),'mean_confidence':round(v['confidence_sum']/max(v['frames'],1),4)})
    valid=sum(int(x['physical_valid']) for x in frames)
    result={'status':'24_FRAME_DIAGNOSTIC','frames':frames,'leg_summary':summary,'physically_valid_fraction':round(valid/max(len(frames),1),4),'all_241_processing_started':False,'note':'Tracking states are evidence summaries; no hidden-leg coordinates are invented.'}
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps({'output':str(out),'frames':len(frames),'physical_valid':valid}))
if __name__=='__main__': main()
