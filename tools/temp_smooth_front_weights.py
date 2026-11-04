import argparse, subprocess
from pathlib import Path
def main():
 p=argparse.ArgumentParser(); p.add_argument('--blender',required=True); p.add_argument('--source',required=True); p.add_argument('--output',required=True); a=p.parse_args(); out=str(Path(a.output).resolve()).replace('\\','/')
 expr=f'''import bpy
bpy.ops.wm.open_mainfile(filepath=r"{Path(a.source).resolve()}"); mesh=next(o for o in bpy.data.objects if o.type=='MESH'); g2=mesh.vertex_groups.get('Leg_Front.L_02'); g3=mesh.vertex_groups.get('Leg_Front.L_03')
changed=0
for v in mesh.data.vertices:
 w2=next((g.weight for g in v.groups if g.group==g2.index),0) if g2 else 0; w3=next((g.weight for g in v.groups if g.group==g3.index),0) if g3 else 0
 if w2>0.25 and w3>0.25:
  total=w2+w3; nw2= max(0,w2-0.10*total); nw3=total-nw2
  g2.add([v.index],nw2,'REPLACE'); g3.add([v.index],nw3,'REPLACE'); changed+=1
bpy.ops.wm.save_as_mainfile(filepath=r'{out}'); print('TEMP_WEIGHT_TEST',changed)'''
 subprocess.run([a.blender,'--background','--python-expr',expr],check=True)
if __name__=='__main__': main()
