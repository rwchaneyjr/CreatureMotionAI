"""External OpenCV/ffmpeg worker; the add-on does not install Python packages."""
import json
import subprocess
import sys
from pathlib import Path
import cv2
import imageio_ffmpeg
import numpy as np

def main():
    out=Path(sys.argv[1]); target=out/'walk_5sec.mp4'
    if target.exists(): raise FileExistsError(target)
    if not all((out/'frames'/f'walk_{i:04}.png').is_file() for i in range(1,121)):
        raise RuntimeError('All 120 actual Blender frames are required; no still-frame substitution.')
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-loglevel','error','-framerate','24','-start_number','1','-i',str(out/'frames/walk_%04d.png'),'-frames:v','120','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(target)],check=True)
    capture=cv2.VideoCapture(str(target)); fps=capture.get(cv2.CAP_PROP_FPS); images=[]
    while True:
        ok,image=capture.read()
        if not ok: break
        images.append(image)
    capture.release()
    if len(images)!=120 or abs(fps-24)>1e-5: raise RuntimeError('MP4 duration must be exactly 120 frames at 24 FPS.')
    motion=[]
    for second in range(5):
        count=[int((cv2.absdiff(images[i],images[i+1]).max(2)>20).sum()) for i in range(second*24,second*24+23)]
        motion.append({'second':second+1,'minimum_changed_pixels':min(count),'mean_changed_pixels':float(np.mean(count))})
    report={'status':'PASS' if all(x['mean_changed_pixels']>500 for x in motion) else 'FAIL',
            'frames':120,'fps':24,'duration_seconds':5,'motion':motion,'visual_approval':'NOT TESTED',
            'note':'Decoded pixel changes confirm temporal change; they do not establish natural gait or reference matching.'}
    (out/'preview_validation.json').write_text(json.dumps(report,indent=2))
    tiles=[]
    for f in [1,14,21,36,54,76,94,116]:
        tile=cv2.resize(images[f-1],(640,360)); cv2.putText(tile,f'Actual MP4 frame {f}',(12,30),0,.7,(255,255,255),2); tiles.append(tile)
    cv2.imwrite(str(out/'decoded_contact_sheet.png'),np.vstack([np.hstack(tiles[i:i+2]) for i in range(0,8,2)]))
    if report['status']!='PASS': raise RuntimeError('Decoded video is static during part of the preview.')
    print(json.dumps(report))

if __name__=='__main__': main()
