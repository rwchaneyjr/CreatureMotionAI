"""Render calibrated front/side leg-identity views from the preserved-rig mask blend."""
import argparse, json
from pathlib import Path
import bpy

FRAMES=(1,6,12,18,24)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--blend',required=True); p.add_argument('--output',required=True)
    a=p.parse_args(); out=Path(a.output).resolve(); out.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(Path(a.blend).resolve()))
    scene=bpy.context.scene
    original=bpy.data.objects.get('CrimsonSpineBehemoth_Mesh')
    mask=bpy.data.objects.get('CMAI_Temporary_Leg_Color_Mask')
    if original: original.hide_render=True
    if mask: mask.hide_render=False
    cameras={'front':'CMAI_Calibrated_Front_Camera','side':'CMAI_Calibrated_Side_Camera'}
    manifest=[]
    for frame in FRAMES:
        scene.frame_set(frame)
        for label,name in cameras.items():
            cam=bpy.data.objects.get(name)
            if not cam: continue
            scene.camera=cam
            path=out/f'{label}_{frame:03d}.png'
            scene.render.filepath=str(path)
            bpy.ops.render.render(write_still=True)
            manifest.append({'frame':frame,'view':label,'path':str(path)})
    (out/'manifest.json').write_text(json.dumps({'status':'diagnostic','frames':list(FRAMES),'renders':manifest},indent=2),encoding='utf-8')
    print(json.dumps({'output':str(out),'renders':len(manifest)}))

if __name__=='__main__': main()
