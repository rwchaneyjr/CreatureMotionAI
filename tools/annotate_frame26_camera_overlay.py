import json, cv2
from pathlib import Path
root=Path(__file__).resolve().parents[1]
src=root/'data/generated/frame26_camera_calibration/camera_overlay.png'
out=root/'data/generated/frame26_camera_calibration/camera_overlay_annotated.png'
im=cv2.imread(str(src))
if im is None: raise SystemExit('overlay missing')
def label(text,xy,color):
    x,y=xy; cv2.arrowedLine(im,(x,y),(x+95,y-35),color,2,tipLength=.15); cv2.putText(im,text,(x+100,y-38),cv2.FONT_HERSHEY_SIMPLEX,.55,color,2,cv2.LINE_AA)
label('dorsal spikes: shape/pose mismatch',(370,280),(0,0,255))
label('tail/body edge: small alignment offset',(45,405),(0,165,255))
label('leg overlap: occlusion/pose, not camera alone',(260,470),(255,0,255))
cv2.putText(im,'FRAME 26 CAMERA REVIEW — CAMERA-ONLY DIAGNOSTIC',(18,28),cv2.FONT_HERSHEY_SIMPLEX,.65,(0,255,255),2,cv2.LINE_AA)
cv2.imwrite(str(out),im)
land=json.loads((root/'data/generated/dlc_training_suggestions.json').read_text())['frames']['26']
report={'status':'UNVERIFIED_CAMERA_NOT_READY_FOR_POSE_FIT','frame':26,'overlay':str(src.resolve()),'annotated_overlay':str(out.resolve()),'camera_fit':{'baseline':'prior perspective comparison was visibly misframed; prior motion-aware landmark RMS was 9.5378 px across its body references','current_orthographic_iou':0.6022237288135593,'current_parameters':{'projection':'ORTHO','ortho_scale':1.22,'target_y':-0.1,'target_z':0.04},'local_refinement':'NOT_RUN','reason':'Residual mismatch is mixed: dorsal/tail silhouette differences and leg overlap are not separable from model pose/occlusion with the resting model.'},'observations':[{'type':'camera_or_global','finding':'small longitudinal/vertical offset remains along tail and dorsal line','confidence':'moderate'},{'type':'model_shape_or_pose','finding':'dorsal spike and torso contour differences remain','confidence':'high'},{'type':'occlusion_or_pose','finding':'leg overlaps differ; static resting legs cannot validate video leg identity','confidence':'high'},{'type':'segmentation','finding':'reference background/ground and colored silhouette affect mask boundary','confidence':'moderate'}],'rearL_landmarks':{k:{'uv':v.get('uv'),'state':v.get('state'),'confidence':v.get('confidence')} for k,v in land.items()},'correspondence':{'rig_chain':['Leg_Rear.L_01','Leg_Rear.L_02','Leg_Rear.L_03'],'status':'UNVERIFIED','reason':'2D image position alone cannot prove these four points belong to the named 3D rear-left chain under the current camera uncertainty.'},'fitting_readiness':{'status':'BLOCKED','leg_fit_justified':False,'missing':['one unambiguous 3D/2D correspondence for the selected Rear.L chain, or a manually confirmed camera/body alignment','separation of static model-shape mismatch from camera error']},'animation_generated':False}
(root/'data/generated/frame26_camera_calibration/camera_landmark_correspondence.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
(root/'data/generated/frame26_camera_calibration/fitting_readiness.json').write_text(json.dumps(report['fitting_readiness'],indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
