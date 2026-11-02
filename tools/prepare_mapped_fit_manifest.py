"""Prepare a conservative 24-frame fitting manifest from identity/readiness data."""
import argparse,json
from pathlib import Path

def main():
    p=argparse.ArgumentParser(); p.add_argument('--readiness',required=True); p.add_argument('--identity-map',required=True); p.add_argument('--output',required=True); a=p.parse_args()
    readiness=json.loads(Path(a.readiness).read_text(encoding='utf-8')); identity=json.loads(Path(a.identity_map).read_text(encoding='utf-8'))
    allowed={x['name'] for x in identity['legs']}; frames=[]
    for frame in readiness['frames']:
        fit=[]; hold=[]
        for leg in frame['legs']:
            if leg['leg'] not in allowed: continue
            (fit if leg['eligible'] else hold).append(leg['leg'])
        frames.append({'frame':frame['frame'],'fit_legs':fit,'hold_legs':hold,'policy':'relative_offset_from_rest','reject_if_collision':True,'reject_if_invalid_angle':True})
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)
    report={'status':'READY_FOR_CONSERVATIVE_FIT','frame_count':len(frames),'leg_count':len(allowed),'frames':frames,'source_identity_map':str(Path(a.identity_map).resolve()),'note':'This manifest does not approve poses; it only prevents fitting uncertain legs.'}
    out.write_text(json.dumps(report,indent=2),encoding='utf-8'); print(json.dumps({'output':str(out),'frames':len(frames)}))
if __name__=='__main__': main()
