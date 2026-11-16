"""Regression test: the eight-leg validator must use the shared ground object."""
from pathlib import Path

def main():
    source=Path(__file__).with_name('validate_eight_leg_walk.py').read_text(encoding='utf-8')
    required=["name=='CMAI_Ground_Contact'", "ground_z=float", "ground_z-min"]
    forbidden=["x['ground']-min"]
    missing=[x for x in required if x not in source]
    present=[x for x in forbidden if x in source]
    if missing or present: raise SystemExit({'status':'FAIL','missing':missing,'forbidden':present})
    print({'status':'PASS','assertions':['shared CMAI_Ground_Contact required','ground_z used for penetration','frame-derived reference prohibited']})
if __name__=='__main__': main()
