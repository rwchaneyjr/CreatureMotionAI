import cv2, os
ref=r'C:\Users\rober\Downloads\SIDEbalaskWALK.mp4'; cap=cv2.VideoCapture(ref); ok,im=cap.read(); cap.release()
bl=cv2.imread('data/generated/standing_baseline_reference_frame1.png'); im=cv2.resize(im,(640,360)); cv2.putText(im,'REFERENCE frame 1',(15,30),0,.8,(0,255,255),2); cv2.putText(bl,'BLENDER standing baseline',(15,30),0,.8,(0,255,255),2)
out='data/generated/standing_baseline_side_by_side.png'; cv2.imwrite(out,cv2.hconcat([im,bl])); print(out)
