"""Compare original FBX rest foot orientations with generated Action frames."""
import argparse, json
from pathlib import Path
import bpy

def read_pose(path, frames):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if path.lower().endswith('.fbx'): bpy.ops.import_scene.fbx(filepath=path)
    else: bpy.ops.wm.open_mainfile(filepath=path)
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    result={}
    for f in frames:
        bpy.context.scene.frame_set(f); result[f]={}
        for b in rig.pose.bones:
            if b.name.startswith('Leg_') and (b.name.endswith('_03') or b.name.endswith('_lower')):
                result[f][b.name]=list(b.rotation_euler)
    return result

def main():
    p=argparse.ArgumentParser(); p.add_argument('--original',required=True); p.add_argument('--generated',required=True); p.add_argument('--output',required=True); a=p.parse_args(); frames=[1,6,12,18,24]
    original=read_pose(a.original,[1]); generated=read_pose(a.generated,frames); base=original[1]; report=[]
    for f in frames:
        for name,rot in generated[f].items():
            ref=base.get(name,rot); delta=[rot[i]-ref[i] for i in range(3)]
            report.append({'frame':f,'bone':name,'rotation':rot,'rest_rotation':ref,'delta':delta,'possible_flip':max(abs(v) for v in delta)>1.57})
    Path(a.output).write_text(json.dumps({'frames':frames,'bones':report,'flipped_count':sum(x['possible_flip'] for x in report)},indent=2),encoding='utf-8'); print(json.dumps({'bones_checked':len(report),'flipped_count':sum(x['possible_flip'] for x in report),'output':a.output}))
if __name__=='__main__': main()
