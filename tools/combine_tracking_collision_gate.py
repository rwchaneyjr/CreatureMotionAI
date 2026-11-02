"""Combine tracking confidence with Blender physical validation."""
import argparse,json
from pathlib import Path

def main():
    p=argparse.ArgumentParser(); p.add_argument('--tracking',required=True); p.add_argument('--collision',required=True); p.add_argument('--output',required=True); a=p.parse_args()
    tracking=json.loads(Path(a.tracking).read_text(encoding='utf-8')); collision=json.loads(Path(a.collision).read_text(encoding='utf-8'))
    by={int(x['frame']):x for x in collision.get('frames',[])}; rows=[]
    for frame in tracking.get('frames',[]):
        c=by.get(int(frame['frame']),{}); reliable=sum(x.get('state')=='tracked' for x in frame.get('legs',[])); physical=bool(c.get('accepted',False)); accepted=physical and reliable>=4
        rows.append({'frame':frame['frame'],'tracked_legs':reliable,'physical_valid':physical,'accepted_for_pose_fit':accepted,'hold_legs':[x['leg'] for x in frame.get('legs',[]) if x.get('state')!='tracked'],'collision_failures':len(c.get('failures',[]))})
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps({'status':'combined_gate','frames':rows,'accepted_frames':sum(int(x['accepted_for_pose_fit']) for x in rows),'policy':'reliable_tracking_and_collision_required','note':'Collider rejects physically invalid candidates; it does not invent hidden-leg positions.'},indent=2),encoding='utf-8'); print(json.dumps({'output':str(out),'accepted_frames':sum(int(x['accepted_for_pose_fit']) for x in rows)}))
if __name__=='__main__': main()
