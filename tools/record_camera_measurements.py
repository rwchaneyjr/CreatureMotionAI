"""Record calibrated two-camera measurements without modifying the scene."""
import argparse,json
from pathlib import Path
import bpy

def flat(m): return [list(row) for row in m]
def main():
 p=argparse.ArgumentParser(); p.add_argument('--output',required=True); a=p.parse_args(); s=bpy.context.scene; out={}
 for label,name in (('side','CMAI_Calibrated_Side_Camera'),('front','CMAI_Calibrated_Front_Camera')):
  c=bpy.data.objects.get(name)
  if not c: continue
  out[label]={'object':name,'location':list(c.location),'rotation_euler':list(c.rotation_euler),'lens':c.data.lens,'sensor_width':c.data.sensor_width,'sensor_height':c.data.sensor_height,'type':c.data.type,'resolution':[s.render.resolution_x,s.render.resolution_y],'matrix_world':flat(c.matrix_world),'projection_matrix':flat(c.calc_matrix_camera(bpy.context.evaluated_depsgraph_get(),x=s.render.resolution_x,y=s.render.resolution_y))}
 result={'status':'recorded','resolution':[s.render.resolution_x,s.render.resolution_y],'panel_resolution':[s.render.resolution_x//2,s.render.resolution_y],'cameras':out,'ground_z':s.get('CMAI_GROUND_Z'),'source_blend':bpy.data.filepath}
 path=Path(a.output); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps({'output':str(path),'cameras':list(out)}))
if __name__=='__main__': main()
