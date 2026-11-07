"""Read-only diagnostic for possible left/right leg-motion mismatch in split video."""
import argparse, json
from pathlib import Path
import cv2, numpy as np

def panel_motion(prev, cur):
    a=cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY); b=cv2.cvtColor(cur, cv2.COLOR_BGR2GRAY)
    h=a.shape[0]; y0=int(h*.48)
    flow=cv2.calcOpticalFlowFarneback(a[y0:],b[y0:],None,.5,3,15,3,5,1.2,0)
    mag=np.linalg.norm(flow,axis=2)
    return float(np.percentile(mag,90)), float(np.mean(mag)), mag

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--video',required=True); ap.add_argument('--output',required=True); ap.add_argument('--preview',required=True); a=ap.parse_args()
    cap=cv2.VideoCapture(a.video); assert cap.isOpened(), f'Cannot open {a.video}'
    n=int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); fps=cap.get(cv2.CAP_PROP_FPS); w=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); h=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)); pw=w//2
    prev=None; rows=[]; writer=cv2.VideoWriter(a.preview,cv2.VideoWriter_fourcc(*'mp4v'),fps,(w,h))
    while True:
        ok,im=cap.read()
        if not ok: break
        left,right=im[:,:pw],im[:,pw:]
        if prev is None: lq=lr=lm=rm=0.0; lmap=rmap=None
        else:
            lq,lm,lmap=panel_motion(prev[:,:pw],left); rq,rm,rmap=panel_motion(prev[:,pw:],right)
        rows.append({'frame':len(rows)+1,'side_motion_p90':lq,'front_motion_p90':lr if prev is None else rq,'side_motion_mean':lm,'front_motion_mean':rm})
        canvas=im.copy(); cv2.line(canvas,(pw,0),(pw,h),(255,255,255),2)
        if prev is not None:
            for x,mp in ((0,lmap),(pw,rmap)):
                if mp is not None:
                    y0=int(h*.48); target=canvas[y0:,x:x+pw]; small=cv2.normalize(mp,None,0,255,cv2.NORM_MINMAX).astype(np.uint8); heat=cv2.applyColorMap(small,cv2.COLORMAP_JET); heat=cv2.resize(heat,(target.shape[1],target.shape[0])); canvas[y0:,x:x+pw]=cv2.addWeighted(target,.72,heat,.28,0)
        cv2.rectangle(canvas,(0,0),(w,48),(255,255,255),-1); r=rows[-1]
        cv2.putText(canvas,f"Frame {r['frame']} | SIDE motion p90 {r['side_motion_p90']:.2f} | FRONT motion p90 {r['front_motion_p90']:.2f} | lower-half optical flow",(8,29),cv2.FONT_HERSHEY_SIMPLEX,.48,(0,0,0),1,cv2.LINE_AA)
        writer.write(canvas); prev=im
    cap.release(); writer.release()
    # Compare event-like lower-panel peaks under offsets and optional panel reversal.
    side=np.array([x['side_motion_p90'] for x in rows]); front=np.array([x['front_motion_p90'] for x in rows])
    def corr(a,b): return float(np.corrcoef(a,b)[0,1]) if np.std(a)>1e-8 and np.std(b)>1e-8 else None
    scores=[]
    for off in range(-12,13):
        if off>=0: x,y=side[off:],front[:len(front)-off]
        else: x,y=side[:len(side)+off],front[-off:]
        scores.append({'offset_frames':off,'direct':corr(x,y),'reversed':corr(x[::-1],y)})
    best=max(scores,key=lambda x: max(x['direct'] or -1,x['reversed'] or -1)); threshold=.75
    status='UNVERIFIED' if max(best['direct'] or -1,best['reversed'] or -1)<threshold else 'PROVISIONAL'
    report={'status':'AUDIT_COMPLETE','video':str(Path(a.video).resolve()),'fps':fps,'frames':n,'panel_resolution':[pw,h],'lower_region':'bottom 52 percent optical-flow signal; not anatomical tracking','scores':scores,'best':best,'decision':status,'stereo_reconstruction':'BLOCKED_UNTIL_LEG_IDENTITY_AND_SYNCHRONY_CONFIRMED','event_interpretation':'Optical-flow peaks indicate motion events but do not identify which foot moved. Manual/DLC leg identity remains required.','preview':str(Path(a.preview).resolve()),'limitations':['No foot detector was used; no foot is automatically declared matching.','Camera perspective and occlusion can change lower-panel flow.','A high correlation is not proof of synchronization.']}
    Path(a.output).parent.mkdir(parents=True,exist_ok=True); Path(a.output).write_text(json.dumps(report,indent=2),encoding='utf-8'); print(json.dumps({'status':status,'best':best,'preview':str(Path(a.preview).resolve())}))
if __name__=='__main__': main()
