"""Optional reference-guided backend using the existing Rear.L planar solver."""
import json, runpy, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TRACKS=ROOT/'data/generated/dlc_tracking_best30/leg_rear_left_tracking.json'
ORIGINAL=ROOT/'data/generated/original_static_standing.blend'
OUTPUT=ROOT/'data/generated/cmai_reference_guided_rearL_24f.blend'
REPORT=ROOT/'data/generated/cmai_reference_guided_rearL_24f_report.json'

def main():
    tracks=json.loads(TRACKS.read_text(encoding='utf-8'))
    by={int(x['frame']):x for x in tracks['frames']}
    anchors=[1,6,12,18,24]; review=[]
    for f in anchors:
        row=by.get(f,{}); low=[k for k,v in row.get('confidence',{}).items() if float(v)<0.6]
        review.append({'frame':f,'status':'MANUAL_REVIEW_REQUIRED' if low else 'HIGH_CONFIDENCE_PROVISIONAL','low_confidence_points':low,'source':row.get('source')})
    # Reuse the established builder; it handles the full-frame interpolation,
    # workspace bounds, Action-slot assignment, and low-confidence holds.
    old=list(sys.argv); sys.argv=['build_planar_rear_left_test.py','--','--blend',str(ORIGINAL),'--tracks',str(TRACKS),'--output',str(OUTPUT),'--report',str(ROOT/'data/generated/cmai_reference_guided_build.json')]
    runpy.run_path(str(ROOT/'tools/build_planar_rear_left_test.py'),run_name='__main__'); sys.argv=old
    import bpy
    action=None
    for a in bpy.data.actions:
        if a.name=='CMAI_RearL_Planar_Test_24F': action=a; break
    if action: action.name='CMAI_RearL_Reference_Guided_24F'
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT))
    result={'status':'GENERATED_REFERENCE_GUIDED_APPROXIMATION','action':action.name if action else None,'anchor_review':review,'manual_review_required':[x for x in review if x['status']=='MANUAL_REVIEW_REQUIRED'],'source_tracks':str(TRACKS),'solver_reused':'tools/build_planar_rear_left_test.py','limitations':['approximate fixed planar projection','not metric 3D','low-confidence points held, not verified','collision requires bounded regional validation'],'original_assets_preserved':True}
    REPORT.write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps(result,indent=2))
if __name__=='__main__': main()
