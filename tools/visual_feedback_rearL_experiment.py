"""Bounded visual-feedback gate for Rear.L; never changes the source action."""
import json, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; G=ROOT/'data/generated'
def load(name):
 p=G/name
 return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
def main():
 cam=load('motion_aware_camera_fit_report.json'); base=load('cmai_reference_guided_rearL_validation.json'); repro=load('cmai_reference_guided_rearL_reprojection.json')
 outblend=G/'cmai_visual_feedback_rearL_24f.blend'; src=G/'cmai_reference_guided_rearL_24f.blend'; shutil.copy2(src,outblend)
 outvideo=G/'cmai_visual_feedback_rearL_comparison.mp4'; srcvideo=G/'cmai_reference_guided_rearL_comparison.mp4'; shutil.copy2(srcvideo,outvideo)
 camera_uncertain=not cam or cam.get('status','').upper() not in {'PASS','VALIDATED'}
 result={'status':'BLOCKED_CAMERA_ALIGNMENT_UNCERTAIN' if camera_uncertain else 'READY_FOR_BOUNDED_OPTIMIZATION','camera_gate':{'status':'FAIL_OR_UNCERTAIN' if camera_uncertain else 'PASS','source_report':str(G/'motion_aware_camera_fit_report.json'),'reason':'Existing fit is approximate and does not establish metric depth or stable body landmark correspondence.' if camera_uncertain else ''},'frames':[1,6,12,18,24],'baseline':{'mean_reprojection_px':repro.get('mean_foot_error_px'),'max_reprojection_px':repro.get('max_foot_error_px'),'ground_penetration':base.get('max_ground_penetration'),'foot_orientation_deg':base.get('max_foot_orientation_deviation_deg'),'mesh_deformed':base.get('mesh_deformed'),'collision':base.get('self_collision')},'optimized':None,'silhouette_error':'UNAVAILABLE_NO_VERIFIED_SEGMENTATION','manual_review_required':[24],'output_blend':str(outblend),'comparison_video':str(outvideo),'policy':'No bone optimization is run until camera alignment and independently observed silhouette/joint evidence are sufficient.'}
 (G/'cmai_visual_feedback_rearL_report.json').write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps(result,indent=2))
if __name__=='__main__': main()
