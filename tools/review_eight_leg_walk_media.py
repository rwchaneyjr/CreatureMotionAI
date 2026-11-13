"""Verify actual renders and create a full-width, approximately aligned comparison."""
import argparse, json, subprocess
from pathlib import Path
import cv2
import numpy as np
import imageio_ffmpeg
from scipy.signal import savgol_filter, find_peaks

def panel(im,title,width=960,height=540):
    out=np.full((height,width,3),245,np.uint8)
    k=min(width/im.shape[1],(height-44)/im.shape[0])
    im=cv2.resize(im,(round(im.shape[1]*k),round(im.shape[0]*k)))
    x=(width-im.shape[1])//2; y=44+(height-44-im.shape[0])//2
    out[y:y+im.shape[0],x:x+im.shape[1]]=im
    cv2.putText(out,title,(14,28),0,.58,(25,25,25),2)
    return out

def decode(path):
    cap=cv2.VideoCapture(str(path)); fps=cap.get(cv2.CAP_PROP_FPS); frames=[]
    while True:
        ok,im=cap.read()
        if not ok: break
        frames.append(im)
    cap.release()
    if not frames or fps<=0: raise RuntimeError(f'Cannot decode {path}')
    return frames,fps

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('directory',type=Path)
    parser.add_argument('--reference',default=r'C:\Users\rober\Downloads\sidewalk8legBalisk.mp4')
    parser.add_argument('--tracking',type=Path,default=Path('data/generated/sidewalk_reference_motion_01.json'))
    args=parser.parse_args(); out=args.directory.resolve()
    video=out/'balisk_eight_leg_review_5sec.mp4'; comparison=out/'balisk_reference_comparison_5sec.mp4'
    for p in [video,comparison,out/'media_validation.json']:
        if p.exists(): raise FileExistsError(p)
    if not all((out/'frames'/f'walk_{f:04}.png').exists() for f in range(1,121)):
        raise RuntimeError('All 120 actual Blender frames are required')
    reference,rfps=decode(args.reference)
    if len(reference)/rfps<5: raise RuntimeError('Reference shorter than five seconds')
    ev=json.loads((out/'saved_action_validation.json').read_text())
    W,H=ev['image_size']; first=ev['frames'][0]
    # Assistant-estimated image features, NOT approved anatomical correspondences.
    ref_shoulder=np.array([929.,340.]); ref_ground=602.
    shoulder=np.array(first['legs']['Front.R']['joints_px'][0]); ground=first['ground_under_front_hip_px'][1]
    scale=(ground-shoulder[1])/(ref_ground-ref_shoulder[1]); offset=shoulder-scale*ref_shoulder
    affine=np.array([[scale,0,offset[0]],[0,scale,offset[1]]])
    alignment={'status':'APPROXIMATE_DISPLAY_ALIGNMENT_UNCALIBRATED','uniform_scale':float(scale),'translation_px':offset.tolist(),
        'reference_shoulder_estimate_px':ref_shoulder.tolist(),'reference_ground_estimate_y':ref_ground,
        'blender_front_R_hip_px':shoulder.tolist(),'blender_ground_y':ground,
        'reference_crop':None,'mirrored_or_rotated':False,
        'limitation':'Two estimated image features only. Body proportions and depth differ; no independent 3D calibration.'}
    def align(im): return cv2.warpAffine(im,affine,(W,H),borderValue=(250,250,250))
    cv2.imwrite(str(out/'standing_comparison.png'),np.hstack([panel(align(reference[0]),'REFERENCE - approximate scale / ground alignment'),panel(cv2.imread(str(out/'standing.png')),'ORIGINAL MODEL - walking standing fit')]))
    (out/'comparison_alignment.json').write_text(json.dumps(alignment,indent=2))
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-loglevel','error','-framerate','24','-start_number','1','-i',str(out/'frames'/'walk_%04d.png'),'-frames:v','120','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(video)],check=True)
    images,fps=decode(video)
    if len(images)!=120 or abs(fps-24)>1e-5: raise RuntimeError('Output duration failed')
    samples=[1,7,14,21,27,34,41,74,114]
    tiles=[panel(images[f-1],f'ACTUAL MP4 - frame {f}',640,360) for f in samples]
    cv2.imwrite(str(out/'encoded_video_contact_sheet.png'),np.vstack([np.hstack(tiles[i:i+3]) for i in range(0,9,3)]))
    changes=[]
    for sec in range(5):
        ds=[cv2.absdiff(images[i],images[i+1]) for i in range(sec*24,min((sec+1)*24-1,119))]
        changes.append({'second':sec+1,'minimum_changed_pixels_gt20':int(min((d.max(2)>20).sum() for d in ds)),
            'mean_changed_pixels_gt20':float(np.mean([(d.max(2)>20).sum() for d in ds]))})
    writer=imageio_ffmpeg.write_frames(str(comparison),(1920,540),fps=24,codec='libx264',pix_fmt_in='rgb24',pix_fmt_out='yuv420p',macro_block_size=1,output_params=['-crf','20','-movflags','+faststart'])
    writer.send(None)
    for i,im in enumerate(images):
        left=panel(align(reference[round(i*rfps/24)]),f'REFERENCE {i/24:.2f}s - UNCALIBRATED')
        right=panel(im,f'BLENDER {i/24:.2f}s - provisional gait timing')
        writer.send(cv2.cvtColor(np.hstack([left,right]),cv2.COLOR_BGR2RGB))
    writer.close()
    compared,cfps=decode(comparison)
    if len(compared)!=120 or abs(cfps-24)>1e-5: raise RuntimeError('Comparison duration failed')
    cv2.imwrite(str(out/'comparison_video_contact_sheet.png'),np.vstack([compared[f-1] for f in [1,14,21,36]]))
    tracking=json.loads(args.tracking.read_text()); metrics={}; pairs={}
    mapping={'V1_rear':'Rear.R','V3':'MidRear.R','V4':'MidFront.R','V5_front':'Front.R'}
    for name,old in tracking['metrics'].items():
        patches=[r['patches'][name] for r in tracking['frames']]
        xy=np.array([[r['x'],r['y']] for r in patches]); valid=np.array([r['confidence']>=.5 for r in patches])
        smooth=savgol_filter(xy,9,2,axis=0)
        peaks,_=find_peaks(-smooth[:,1],prominence=10,distance=18)
        peaks=[int(p) for p in peaks if valid[max(0,p-2):min(len(valid),p+3)].all()]
        metrics[name]={'status':'UNVERIFIED_FLOW_PATCH','flow_consistent_frames':int(valid.sum()),
            'body_relative_forward_range_px':old['horizontal_range_px'],'raw_vertical_range_px':float(np.ptp(smooth[valid,1])),
            'raw_image_lift_peaks':[p+1 for p in peaks],'peak_intervals_frames':np.diff(peaks).tolist(),
            'correction':'Lift peaks use image ground, not vertical coordinates relative to the moving body patch.'}
        if name not in mapping: continue
        leg=mapping[name]; p=np.array([r['legs'][leg]['joints_px'][-1] for r in ev['frames'][:120]])
        body=np.array([r['legs'][leg]['joints_px'][0] for r in ev['frames'][:120]])
        rxy=smooth*scale; rb=np.array([[r['patches']['body']['x'],r['patches']['body']['y']] for r in tracking['frames']])*scale
        rx=rxy[:,0]-rb[:,0]; bx=p[:,0]-body[:,0]
        rd=np.c_[rx-rx[valid].mean(),rxy[:,1]-rxy[valid,1].mean()]
        bd=np.c_[bx-bx[valid].mean(),p[:,1]-p[valid,1].mean()]
        err=np.linalg.norm(rd-bd,axis=1)
        bp,_=find_peaks(-savgol_filter(p[:,1],9,2),prominence=4,distance=18)
        pairs[name]={'candidate_leg':leg,'identity':'UNVERIFIED','aligned_reference_forward_range_px':float(np.ptp(rx[valid])),
            'blender_forward_range_px':float(np.ptp(bx)),'blender_lift_peaks':[int(v+1) for v in bp],
            'centered_trajectory_RMSE_px':float(np.sqrt(np.mean(err[valid]**2))),
            'limitation':'Image patch and bone tail are different features. Offset-free style comparison, NOT calibrated anatomical reprojection error.'}
    report={'video':str(video),'comparison_video':str(comparison),'decoded_frames':120,'fps':24,'duration_seconds':5,
        'pixel_change_by_second':changes,'cycle_repeat_mean_pixel_error':float(np.mean([cv2.absdiff(images[i],images[i+40]).mean() for i in range(80)])),
        'reference':str(Path(args.reference).resolve()),'reference_duration_seconds':len(reference)/rfps,'reference_fps':rfps,
        'alignment':alignment,'timing':'Same original elapsed time. Modeled 40-frame cycle approximately follows 38-40-frame front interval. No time warping.',
        'reference_metrics':metrics,'provisional_trajectory_comparison':pairs,
        'visual_status':'REQUIRES_INSPECTION','exact_video_match':'NOT_CLAIMED'}
    (out/'media_validation.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'video':str(video),'comparison':str(comparison),'duration':5,'changes':changes,'trajectory_comparison':pairs},indent=2))

if __name__=='__main__': main()
