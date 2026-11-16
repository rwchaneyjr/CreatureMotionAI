"""Create a simple readable anatomy candidate sheet from a detector report."""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

report_path=Path(sys.argv[1]); output=Path(sys.argv[2])
data=json.loads(report_path.read_text())
W,H=900,650; image=Image.new('RGB',(W,H),'white'); draw=ImageDraw.Draw(image)
font=ImageFont.load_default()
draw.text((20,15),f"{data['armature']} — {data['status']}",fill='black',font=font)
draw.text((20,32),f"Selected: {data['selected_leg_count']} | Confidence: {data['mapping_confidence']} | Confirmed: {data['confirmed']}",fill='black',font=font)
chains=data['selected_chains']; allpts=[p for c in chains for p in c['points']]
xs=[p[0] for p in allpts] or [0,1]; ys=[p[1] for p in allpts] or [0,1]
minx,maxx=min(xs),max(xs); miny,maxy=min(ys),max(ys)
def project(p):
    x=50+(p[0]-minx)/max(1e-6,maxx-minx)*800
    y=580-(p[1]-miny)/max(1e-6,maxy-miny)*500
    return int(x),int(y)
colors={'HIGH':'#138a36','MEDIUM':'#c77b00','LOW':'#c62828'}
for i,c in enumerate(chains):
    pts=[project(p) for p in c['points']]; color=colors.get(c['confidence'],'#555555')
    draw.line(pts,fill=color,width=5)
    for j,p in enumerate(pts):
        draw.ellipse((p[0]-6,p[1]-6,p[0]+6,p[1]+6),fill=color,outline='black')
        draw.text((p[0]+8,p[1]-8),('hip','joint','foot','end')[j],fill='black',font=font)
    draw.text((pts[0][0]+8,pts[0][1]+10),f"{i+1}: {c['confidence']} {c['score']:.2f}",fill=color,font=font)
draw.text((20,610),'Green HIGH | amber MEDIUM | red LOW — proposals are unconfirmed',fill='black',font=font)
output.parent.mkdir(parents=True,exist_ok=True); image.save(output)
print(output)
