"""Read-only comparison of original standing and generated walk blends."""
import argparse, json, sys
from pathlib import Path
import bpy

LEGS=['Leg_Front.L','Leg_Front.R','Leg_MidFront.L','Leg_MidFront.R','Leg_MidRear.L','Leg_MidRear.R','Leg_Rear.L','Leg_Rear.R']
FRAMES=[1,6,12,18,24]
def v(x): return [round(float(a),8) for a in x]
def mat(m): return [[round(float(x),8) for x in row] for row in m]
def action_info(a):
    if not a: return None
    info={'name':a.name,'frame_range':list(a.frame_range),'is_empty':getattr(a,'is_empty',None),'fcurves':[]}
    try:
        for layer in a.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for fc in bag.fcurves:
                        info['fcurves'].append({'data_path':fc.data_path,'index':fc.array_index,'keyframes':len(fc.keyframe_points),'range':[float(fc.range()[0]),float(fc.range()[1])]})
    except Exception as exc: info['fcurve_error']=repr(exc)
    return info
def snapshot(path):
    bpy.ops.wm.open_mainfile(filepath=str(Path(path).resolve())); s=bpy.context.scene; arm=next(o for o in s.objects if o.type=='ARMATURE'); mesh=next((o for o in s.objects if o.type=='MESH'),None)
    bones={b.name:{'parent':b.parent.name if b.parent else None,'children':[c.name for c in b.children],'length':b.length,'head':v(b.head_local),'tail':v(b.tail_local),'matrix':mat(b.matrix_local)} for b in arm.data.bones}
    modifiers=[]; materials=[]; vertex_samples=[]
    if mesh:
        modifiers=[{'name':m.name,'type':m.type,'object':m.object.name if getattr(m,'object',None) else None} for m in mesh.modifiers]
        materials=[m.name if m else None for m in mesh.data.materials]
    action_info_row=action_info(arm.animation_data.action if arm.animation_data else None)
    feet={}
    verts={}
    for f in FRAMES:
        s.frame_set(f); bpy.context.view_layer.update(); feet[f]={n:v(arm.matrix_world@arm.pose.bones[n+'_03'].tail) for n in LEGS};
        if mesh:
            ev=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get()); data=ev.to_mesh(); verts[f]=[v(x.co) for x in list(data.vertices)[:20]]; ev.to_mesh_clear()
    cameras=[{'name':o.name,'location':v(o.location),'lens':o.data.lens} for o in s.objects if o.type=='CAMERA']
    constraints={p.name:[{'name':c.name,'type':c.type,'chain_count':getattr(c,'chain_count',None),'influence':c.influence,'target':c.target.name if c.target else None} for c in p.constraints] for p in arm.pose.bones if p.constraints}
    return {'path':str(Path(path).resolve()),'bones':bones,'bone_count':len(bones),'mesh':mesh.name if mesh else None,'modifiers':modifiers,'materials':materials,'action':action_info_row,'feet':feet,'vertices':verts,'cameras':cameras,'constraints':constraints,'frame_range':[s.frame_start,s.frame_end]}
def main():
    p=argparse.ArgumentParser(); p.add_argument('--original',required=True); p.add_argument('--generated',required=True); p.add_argument('--output',required=True); argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]; a=p.parse_args(argv)
    orig=snapshot(a.original); gen=snapshot(a.generated); checks={}
    checks['bone_count_38']=orig['bone_count']==38 and gen['bone_count']==38
    checks['bone_names_match']=set(orig['bones'])==set(gen['bones'])
    checks['parents_match']=all(orig['bones'][n]['parent']==gen['bones'][n]['parent'] for n in orig['bones'] if n in gen['bones'])
    checks['rest_transforms_match']=all(max(abs(orig['bones'][n]['head'][i]-gen['bones'][n]['head'][i]) for i in range(3))<1e-6 and max(abs(orig['bones'][n]['tail'][i]-gen['bones'][n]['tail'][i]) for i in range(3))<1e-6 for n in orig['bones'] if n in gen['bones'])
    checks['armature_modifier_preserved']=orig['modifiers']==gen['modifiers']
    checks['materials_present']=bool(orig['materials']) and bool(gen['materials']) and set(orig['materials'])==set(gen['materials'])
    checks['action_exists']=bool(gen['action']) and bool(gen['action'].get('fcurves'))
    foot_diffs={};
    for f in FRAMES: foot_diffs[f]={n:sum((gen['feet'][f][n][i]-orig['feet'][f][n][i])**2 for i in range(3))**0.5 for n in LEGS}
    checks['evaluated_feet_change']=max(foot_diffs[12].values())>1e-4
    checks['evaluated_mesh_changes']=gen['vertices'].get(1)!=gen['vertices'].get(12)
    report={'status':'investigation_complete','checks':checks,'original':orig,'generated':gen,'foot_world_differences':foot_diffs,'root_causes':[]}
    if not checks['action_exists']: report['root_causes'].append('Generated Action has no readable F-curves in Blender 5 channel bags.')
    if not checks['evaluated_mesh_changes']: report['root_causes'].append('Evaluated mesh vertices do not change despite Action/targets.')
    if checks['evaluated_feet_change'] and not checks['evaluated_mesh_changes']: report['root_causes'].append('IK target/bone endpoints move but mesh deformation is not changing; inspect armature modifier or evaluated dependency graph.')
    if not checks['materials_present']: report['root_causes'].append('Generated scene material assignments differ or are missing.')
    Path(a.output).write_text(json.dumps(report,indent=2),encoding='utf-8'); print(json.dumps({'output':a.output,'checks':checks,'root_causes':report['root_causes']}))
if __name__=='__main__': main()
