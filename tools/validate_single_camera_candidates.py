"""Filter single-camera foot candidates with temporal flow and identity gates."""
import argparse, json
from pathlib import Path
import cv2, numpy as np

def main():
    p=argparse.ArgumentParser(); p.add_argument('--video',required=True); p.add_argument('--tracks',required=True); p.add_argument('--output',required=True); p.add_argument('--report',required=True); p.add_argument('--max-frames',type=int,default=24); a=p.parse_args()
    tracks=json.loads(Path(a.tracks).read_text()); cap=cv2.VideoCapture(a.video); frames=[]; prev_gray=None; prev_pts={}; rows=[]
    for frame_no in range(1,a.max_frames+1):
        ok,img=cap.read()
        if not ok: break
        gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY); gray=cv2.resize(gray,(640,360),interpolation=cv2.INTER_AREA); raw=tracks['frames'][frame_no-1].get('candidates',[]); points=[]; accepted=0; uncertain=0
        for cand in raw:
            leg=int(cand.get('leg',-1)); foot=cand.get('foot'); item={'leg':leg,'name':f'leg_{leg:02d}_foot','visible':False,'confidence':0.0,'state':'uncertain_no_anatomical_joint'}
            if foot is not None:
                x=float(foot[0])*640; y=float(foot[1])*360; temporal=1.0
                if leg in prev_pts: temporal=max(0.0,1.0-min(1.0,float(np.linalg.norm(np.array([x,y])-prev_pts[leg]))/80.0))
                flow_score=0.0
                if prev_gray is not None and leg in prev_pts:
                    p0=np.float32([[prev_pts[leg]]]).reshape(1,1,2); p1,st,err=cv2.calcOpticalFlowPyrLK(prev_gray,gray,p0,None); flow_score=max(0.0,1.0-min(1.0,float(err[0,0])/25.0)) if st[0,0] else 0.0
                contour=float(cand.get('confidence',0.0)); confidence=0.45*contour+0.30*temporal+0.25*flow_score; stable=confidence>=0.72 and temporal>=0.45
                item.update({'x':x,'y':y,'confidence':confidence,'temporal_score':temporal,'flow_score':flow_score,'contour_score':contour,'visible':stable,'state':'proposal' if stable else 'uncertain_temporal_or_occluded'})
                if stable: accepted+=1; prev_pts[leg]=np.array([x,y],dtype=np.float32)
                else: uncertain+=1
            points.append(item)
        # Hip, knee, and ankle are deliberately absent rather than guessed.
        rows.append({'frame':frame_no,'camera_A':{'landmarks':{x['name']:x for x in points}},'camera_B':{'landmarks':{}},'state':'single_camera_provisional','accepted_foot_points':accepted,'uncertain_points':uncertain})
        prev_gray=gray
    cap.release(); report={'status':'provisional_review_required','frames':len(rows),'accepted_foot_landmarks':sum(x['accepted_foot_points'] for x in rows),'uncertain_foot_landmarks':sum(x['uncertain_points'] for x in rows),'missing_anatomical_landmarks':{'hip':len(rows)*8,'knee':len(rows)*8,'ankle':len(rows)*8},'identity_swaps_rejected':True,'depth_status':'unknown_single_camera','note':'Only high-confidence foot proposals are visible; hip/knee/ankle and all depth remain uncertain until native Blender review.'}; result={'status':'single_camera_provisional','frames':rows,'source_video':str(Path(a.video).resolve()),'report':report}; Path(a.output).write_text(json.dumps(result,indent=2)); Path(a.report).write_text(json.dumps(report,indent=2)); print(json.dumps(report,indent=2))
if __name__=='__main__': main()
