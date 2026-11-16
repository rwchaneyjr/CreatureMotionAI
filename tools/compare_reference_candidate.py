import cv2, json
from pathlib import Path
import numpy as np

root=Path(r'C:\Users\rober\CreatureMotionAI')
ref=Path(r'C:\Users\rober\Downloads\2VIEWSBALISK SYNCWALK.mp4')
earlier=root/'data/generated/balisk_camera_baseline_walk_01/walk_5sec.mp4'
current=root/'data/generated/e2e_balisk_test/builder/encode/walk_5sec.mp4'
out=root/'data/generated/reference_guided_improvement_01'; out.mkdir(parents=True,exist_ok=True)
videos=[cv2.VideoCapture(str(p)) for p in (ref,earlier,current)]
writer=cv2.VideoWriter(str(out/'reference_earlier_current_comparison.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),24,(1920,360))
frames=0; diff=[]
while True:
    vals=[]
    for i,cap in enumerate(videos):
        ok,im=cap.read()
        if not ok: break
        if i==0:
            h,w=im.shape[:2]; im=im[:,:w//2]
        im=cv2.resize(im,(640,360)); vals.append(im)
    if len(vals)!=3: break
    labels=['REFERENCE SIDE VIEW (identity uncertain)','EARLIER BASELINE CANDIDATE','CURRENT E2E']
    for im,label in zip(vals,labels):
        cv2.rectangle(im,(0,0),(639,38),(0,0,0),-1)
        cv2.putText(im,label,(10,26),cv2.FONT_HERSHEY_SIMPLEX,.55,(0,220,255),2,cv2.LINE_AA)
    writer.write(cv2.hconcat(vals)); frames+=1
    # Candidate/current image difference only; not a metric of truth.
    diff.append(float(np.mean(cv2.absdiff(vals[1],vals[2]))))
for cap in videos: cap.release()
writer.release()
report={'status':'REVIEW_REQUIRED','reference':str(ref),'earlier_candidate':str(earlier),'current':str(current),'frames_compared':frames,'mean_candidate_current_pixel_difference':sum(diff)/len(diff) if diff else None,'measurement_policy':{'reference_leg_identity':'UNVERIFIED','individual_leg_metrics':'NOT_COMPUTED','reliable_metrics':['three_view_frame_alignment','candidate_vs_current_pixel_difference'],'caveat':'Reference and Blender camera/scale are not guaranteed metrically aligned; pixel differences are diagnostic only.'},'candidate_action':'Earlier baseline preserved as a separate candidate; no original Action overwritten.','mechanical_validation':'NOT_RE-RUN_IN_THIS_COMPARISON','collision_validation':'NOT_RE-RUN_IN_THIS_COMPARISON'}
(out/'reference_guided_improvement_report.json').write_text(json.dumps(report,indent=2))
print(out/'reference_earlier_current_comparison.mp4')
