import cv2, numpy as np
from pathlib import Path
out=Path("data/generated/standing_contact_fit_v3")
cap=cv2.VideoCapture(r"C:\Users\rober\Downloads\SIDEbalaskWALK.mp4")
frames=[]
for f in [1,9,17,25,33,41,49,57]:
    cap.set(cv2.CAP_PROP_POS_FRAMES,f-1)
    ok,im=cap.read()
    if not ok: raise RuntimeError(f)
    # video side panel is on the left; retain the full crop without distortion
    im=im[:,:640]
    im=cv2.resize(im,(480,540))
    cv2.putText(im,f"Reference frame {f}",(12,28),0,.7,(0,0,0),2)
    frames.append(im)
cv2.imwrite(str(out/"reference_phases.png"),np.vstack([np.hstack(frames[:4]),np.hstack(frames[4:])]))
cap.release()
