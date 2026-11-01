"""Loop the corrected one-second rig and IK-target animation five times."""
import argparse, sys
from pathlib import Path
import bpy

def main():
    p=argparse.ArgumentParser(); p.add_argument('--input',required=True); p.add_argument('--output',required=True); p.add_argument('--frames',type=int,default=120); a=p.parse_args(); bpy.ops.wm.open_mainfile(filepath=a.input)
    animated=[]
    for obj in bpy.context.scene.objects:
        if not obj.animation_data or not obj.animation_data.action: continue
        action=obj.animation_data.action; start,end=1,24
        track=obj.animation_data.nla_tracks.new(); track.name='CMAI_5Second_Loop'; strip=track.strips.new('CMAI_OneSecond_Cycle',1,action); strip.action_frame_start=start; strip.action_frame_end=end; strip.repeat=5.0
        obj.animation_data.action=None; animated.append(obj.name)
    s=bpy.context.scene; s.frame_start=1; s.frame_end=a.frames; s.render.fps=24; s.frame_set(1); Path(a.output).parent.mkdir(parents=True,exist_ok=True); bpy.ops.wm.save_as_mainfile(filepath=a.output); print({'output':a.output,'frames':a.frames,'animated_objects':animated})
if __name__=='__main__': main()
