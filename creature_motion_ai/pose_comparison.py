"""Score actual pose renders against side images; never infer video joint names."""
import json
import sys
from pathlib import Path
import cv2
import numpy as np
from .reference_evidence import foreground_mask


def reference(video, frame):
    capture=cv2.VideoCapture(str(video)); capture.set(cv2.CAP_PROP_POS_FRAMES,frame-1)
    ok,image=capture.read(); capture.release()
    if not ok: raise ValueError(f'Reference frame {frame} unavailable')
    image=cv2.resize(image,(640,360)); mask=foreground_mask(image)
    if mask is None: raise ValueError('Reference segmentation unavailable')
    return image,mask>0


def score(reference_mask, path):
    image=cv2.imread(str(path))
    if image is None: raise ValueError('Render unavailable: '+str(path))
    mask=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)>100
    iou=float((reference_mask&mask).sum()/max(1,(reference_mask|mask).sum()))
    body=body_metrics(reference_mask,mask)
    edge=int(mask[0].sum()+mask[-1].sum()+mask[:,0].sum()+mask[:,-1].sum())
    return dict(silhouette_iou=iou,edge_foreground_pixels=edge,**body,
                approximate_camera_pass=bool(edge==0 and body['body_roi_iou']>=.7 and body['centroid_error_px']<=10))


def body_metrics(reference_mask, model_mask):
    # Same fixed upper-62% torso proxy as the existing calibration scorer.
    x,y,w,h=cv2.boundingRect(reference_mask.astype('uint8'))
    roi=np.zeros_like(reference_mask)
    roi[y:y+int(.62*h),x+int(.1*w):x+int(.9*w)]=True
    a=reference_mask&roi; b=model_mask&roi
    ay,ax=np.where(a); by,bx=np.where(b)
    error=float(np.hypot(ax.mean()-bx.mean(),ay.mean()-by.mean())) if len(ax) and len(bx) else 999.
    return dict(body_roi_iou=float((a&b).sum()/max(1,(a|b).sum())),centroid_error_px=error)


def framing_translation(reference_mask, path):
    """Bounded framing-only correction; preserve lens, view direction and rig."""
    from scipy.optimize import minimize
    mask=cv2.imread(str(path),0)>100
    def warp(p):
        return cv2.warpAffine(mask.astype('uint8'),np.float32([[1,0,p[0]],[0,1,p[1]]]),(640,360),flags=cv2.INTER_NEAREST)>0
    def loss(p):
        m=body_metrics(reference_mask,warp(p))
        return 1-m['body_roi_iou']+.001*m['centroid_error_px']
    result=minimize(loss,[0.,0.],method='Powell',bounds=[(-16,16),(-16,16)],options={'maxiter':30})
    delta=result.x if loss(result.x)<loss([0,0]) else np.zeros(2)
    return {'dx_px':float(delta[0]),'dy_px':float(delta[1]),'before':body_metrics(reference_mask,mask),
            'predicted_after':body_metrics(reference_mask,warp(delta)),
            'method':'Bounded camera shift only, fixed torso ROI; must be checked with actual rerender',
            'metric_calibration':'UNVERIFIED'}


def run(output, phase_only=False):
    output=Path(output).resolve(); request=json.loads((output/'request.json').read_text())
    manifest=request['manifest']; inputs=manifest['inputs']
    ref,mask=reference(inputs['side_video'],request['reference_frame'])
    if phase_only:
        samples=json.loads((output/'phase_samples.json').read_text())['samples']
        rows=[dict(row,**score(mask,output/f'phase_{row["frame"]}_side.png')) for row in samples]
        best=max([row for row in rows if row.get('lifted_legs')] or rows,key=lambda r:r['silhouette_iou'])
        result={'selected_frame':best['frame'],'rows':rows,'synchronization':'UNVERIFIED',
                'framing_adjustment':framing_translation(mask,output/f'phase_{best["frame"]}_side.png'),
                'method':'coarse single-pose silhouette comparison; not temporal synchronization'}
        (output/'phase_selection.json').write_text(json.dumps(result,indent=2)); return
    result=json.loads((output/'pose_candidates.json').read_text())
    rows=result['candidates']; front_refs=[]
    if inputs.get('front_video'):
        front_refs=[(frame,*reference(inputs['front_video'],frame)) for frame in (1,26,61,121,201)]
    for row in rows:
        row['side']=score(mask,output/f'candidate_{row["candidate"]}_side.png')
        row['front_similar_pose'] = max([dict(frame=frame,**score(fmask,output/f'candidate_{row["candidate"]}_front.png'))
                                       for frame,_,fmask in front_refs],key=lambda x:x['silhouette_iou']) if front_refs else None
    baseline=rows[0]; accepted=[]
    for row in rows:
        row['side_iou_gain']=row['side']['silhouette_iou']-baseline['side']['silhouette_iou']
        row['rejection_reasons']=[]
        if row['candidate']==0: continue
        if row['side_iou_gain']<.002: row['rejection_reasons'].append('Side silhouette gain below 0.002')
        if not row['mechanical_pass']: row['rejection_reasons'].append('Knee/contact/collision validation did not pass')
        if not row['side']['approximate_camera_pass']: row['rejection_reasons'].append('Approximate camera alignment check did not pass')
        if row['side']['edge_foreground_pixels']: row['rejection_reasons'].append('Model intersects image boundary; full silhouette is not observed')
        if row['front_similar_pose'] and row['front_similar_pose']['silhouette_iou']+1e-4<baseline['front_similar_pose']['silhouette_iou']:
            row['rejection_reasons'].append('Secondary front silhouette regressed')
        row['accepted_single_pose']=not row['rejection_reasons']
        if row['accepted_single_pose']: accepted.append(row)
    best=max(accepted,key=lambda r:r['side_iou_gain']) if accepted else baseline
    illustrative=max(rows,key=lambda r:r['side_iou_gain'])
    result.update(status='PASS_APPROXIMATE_SINGLE_POSE' if accepted else 'RETAINED_BASELINE',best_candidate=best['candidate'],
                  best_visual_candidate=illustrative['candidate'],walking_action_replaced=False,
                  full_cycle_validation='NOT RUN; single-pose test only',metric_3d_reconstruction='UNVERIFIED',
                  joint_reprojection_error_px=None,front_timing_used=False)
    tiles=[]
    for label,image in [('Reference side pose',ref),('Working animation',cv2.imread(str(output/'candidate_0_side.png'))),
                        (f'Candidate {illustrative["candidate"]} — '+result['status'],cv2.imread(str(output/f'candidate_{illustrative["candidate"]}_side.png')))]:
        cv2.rectangle(image,(0,0),(640,30),(30,30,30),-1)
        cv2.putText(image,label.replace('—','-'),(8,21),0,.48,(255,255,255),1); tiles.append(image)
    cv2.imwrite(str(output/'side_pose_comparison.png'),np.hstack(tiles))
    surface=[]
    for index in (0,illustrative['candidate']):
        surface.append(cv2.imread(str(output/f'candidate_{index}_surface_side.png')))
    cv2.imwrite(str(output/'side_surface_comparison.png'),np.hstack([ref,*surface]))
    if front_refs:
        f=illustrative['front_similar_pose']['frame']; front_image=next(im for frame,im,_ in front_refs if frame==f)
        cv2.imwrite(str(output/'front_pose_comparison.png'),np.hstack([front_image,cv2.imread(str(output/'candidate_0_front.png')),cv2.imread(str(output/f'candidate_{illustrative["candidate"]}_front.png'))]))
    (output/'pose_improvement_report.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'status':result['status'],'best_candidate':result['best_candidate'],'report':str(output/'pose_improvement_report.json')}))


if __name__=='__main__': run(sys.argv[1],len(sys.argv)>2 and sys.argv[2]=='phase')
