"""Search side-camera distance/height against one MP4 reference frame."""
import argparse, subprocess, json
from pathlib import Path
import cv2, numpy as np

def score(ref, render):
    ref = cv2.resize(ref, (render.shape[1], render.shape[0]))
    rg = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY); bg = cv2.cvtColor(render, cv2.COLOR_BGR2GRAY)
    _, rm = cv2.threshold(rg, 150, 255, cv2.THRESH_BINARY_INV); _, bm = cv2.threshold(bg, 20, 255, cv2.THRESH_BINARY)
    return float(np.logical_and(rm > 0, bm > 0).sum() / max(np.logical_or(rm > 0, bm > 0).sum(), 1))

def main():
    p=argparse.ArgumentParser(); p.add_argument('--blend',required=True); p.add_argument('--video',required=True); p.add_argument('--output',required=True); p.add_argument('--blender',required=True); p.add_argument('--work',required=True); p.add_argument('--view',choices=('side','front'),default='side'); args=p.parse_args()
    work=Path(args.work); work.mkdir(parents=True,exist_ok=True); cap=cv2.VideoCapture(args.video); cap.set(cv2.CAP_PROP_POS_FRAMES,11); ok,ref=cap.read(); cap.release()
    best=(-1,None)
    for distance in (2.2,2.6,3.0,3.4,3.8,4.2):
        for height in (0.0,0.15,0.3,0.45):
            out=work/f'candidate_{distance}_{height}.png'
            location = f"(-{distance},0,{height})" if args.view == 'side' else f"(0,-{distance},{height})"
            expr=f"import bpy; from mathutils import Vector; bpy.ops.wm.open_mainfile(filepath=r'{args.blend}'); s=bpy.context.scene; s.render.engine='BLENDER_WORKBENCH'; s.render.resolution_x=640; s.render.resolution_y=360; s.render.resolution_percentage=100; d=bpy.data.cameras.get('CMAI_MP4_Side_Camera') or bpy.data.cameras.new('CMAI_MP4_Side_Camera'); c=bpy.data.objects.get('CMAI_MP4_Side_Camera') or bpy.data.objects.new('CMAI_MP4_Side_Camera',d); (bpy.context.collection.objects.link(c) if c.name not in [o.name for o in s.objects] else None); c.location={location}; c.rotation_euler=(Vector((0,0,0))-c.location).to_track_quat('-Z','Y').to_euler(); s.camera=c; s.render.filepath=r'{out}'; s.frame_set(1); bpy.ops.render.render(write_still=True)"
            subprocess.run([args.blender,'--background','--python-expr',expr],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
            image=cv2.imread(str(out)); value=score(ref,image)
            if value>best[0]: best=(value,(distance,height))
    location = f"(-{distance},0,{height})" if args.view == 'side' else f"(0,-{distance},{height})"
    expr=f"import bpy; from mathutils import Vector; bpy.ops.wm.open_mainfile(filepath=r'{args.blend}'); d=bpy.data.cameras.get('CMAI_MP4_Side_Camera') or bpy.data.cameras.new('CMAI_MP4_Side_Camera'); c=bpy.data.objects.get('CMAI_MP4_Side_Camera') or bpy.data.objects.new('CMAI_MP4_Side_Camera',d); (bpy.context.collection.objects.link(c) if c.name not in [o.name for o in bpy.context.scene.objects] else None); c.location={location}; c.rotation_euler=(Vector((0,0,0))-c.location).to_track_quat('-Z','Y').to_euler(); bpy.context.scene.camera=c; bpy.ops.wm.save_as_mainfile(filepath=r'{args.output}')"
    subprocess.run([args.blender,'--background','--python-expr',expr],check=True)
    report={'best_iou':best[0],'camera_distance':distance,'camera_height':height,'output':args.output}
    Path(args.output).with_suffix('.camera_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8'); print(json.dumps(report))
if __name__=='__main__': main()
