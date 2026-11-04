import argparse, subprocess
from pathlib import Path
def main():
 p=argparse.ArgumentParser(); p.add_argument('--blender',required=True); p.add_argument('--blend',required=True); p.add_argument('--output',required=True); a=p.parse_args(); out=str(Path(a.output).resolve()).replace('\\','/')
 expr=f'''import bpy
bpy.ops.wm.open_mainfile(filepath=r"{Path(a.blend).resolve()}"); arm=next(o for o in bpy.data.objects if o.type=='ARMATURE'); ad=arm.animation_data; act=ad.action
if act and len(act.slots): ad.action_slot=act.slots[0]
bpy.ops.wm.save_as_mainfile(filepath=r'{out}')
print('ACTION_SLOT_REPAIRED',act.name if act else None, bool(ad.action_slot))'''
 subprocess.run([a.blender,'--background','--python-expr',expr],check=True)
if __name__=='__main__': main()
