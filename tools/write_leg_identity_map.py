"""Write the stable eight-leg identity map used by matching and validation."""
import argparse, json
from pathlib import Path

LEGS=("Leg_Front.L","Leg_Front.R","Leg_MidFront.L","Leg_MidFront.R","Leg_MidRear.L","Leg_MidRear.R","Leg_Rear.L","Leg_Rear.R")
COLORS=("red","orange","yellow","green","cyan","blue","purple","magenta")

def main():
    p=argparse.ArgumentParser(); p.add_argument('--output',required=True); a=p.parse_args()
    rows=[]
    for i,(name,color) in enumerate(zip(LEGS,COLORS),1):
        rows.append({'id':i,'name':name,'color':color,'bones':[f'{name}_{n:02d}' for n in (1,2,3)],'landmarks':[f'{name}_{n:02d}_head' for n in (1,2,3)]+[f'{name}_03_tail'],'policy':'use_observation_if_visible_else_previous_valid_pose'})
    out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({'schema':'CMAI_leg_identity_v1','leg_count':8,'source_rig':'original_static_standing.blend','legs':rows,'overlap_policy':'uncertain_not_guessed','fit_policy':'baseline_relative_offsets','collision_policy':'reject_self_collision_or_ground_penetration'},indent=2),encoding='utf-8')
    print(json.dumps({'output':str(out),'legs':8}))
if __name__=='__main__': main()
