import cv2
from pathlib import Path

root=Path(__file__).resolve().parents[1]/'data/generated/front_l_solver_comparison'
methods=[('CUSTOM rest-relative', 'custom_renders'),('BLENDER IK','blender_ik_renders'),('FK rest-relative','fk_renders')]
frames=[1,6,12,18,24]
tiles=[]
for label,folder in methods:
    row=[]
    for f in frames:
        p=root/folder/f'frame_{f:02d}.png'
        im=cv2.imread(str(p))
        if im is None: raise FileNotFoundError(p)
        im=cv2.resize(im,(480,270))
        cv2.putText(im,f'{label}  frame {f}',(10,25),cv2.FONT_HERSHEY_SIMPLEX,.65,(0,255,255),2,cv2.LINE_AA)
        row.append(im)
    tiles.append(cv2.hconcat(row))
out=root/'front_l_solver_comparison_contact_sheet.png'
cv2.imwrite(str(out),cv2.vconcat(tiles))
print(out)
