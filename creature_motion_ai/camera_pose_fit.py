"""One bounded pose iteration using the existing leg solver and evaluated mesh.

This is a diagnostic copy of the best walk. No curve in the source Action is
changed, and anonymous silhouette evidence never becomes a named video joint.
"""
import json
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from . import reference_walk as walk
from .reference_evidence import file_hash


def render_setup(scene, mesh, profiles):
    for obj in scene.objects:
        if obj.type == 'MESH': obj.hide_render = obj != mesh
    scene.render.engine='BLENDER_WORKBENCH'
    scene.render.resolution_x=640; scene.render.resolution_y=360; scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'; scene.render.film_transparent=False
    shading=scene.display.shading; shading.light='FLAT'; shading.color_type='SINGLE'; shading.single_color=(1,1,1)
    shading.background_type='WORLD'; shading.show_shadows=False; shading.show_cavity=False; shading.show_specular_highlight=False
    scene.world=bpy.data.worlds.new('CMAI_Pose_Diagnostic_World'); scene.world.color=(0,0,0)
    cameras={}
    for profile in profiles:
        data=bpy.data.cameras.new('CMAI_Pose_'+profile['view'])
        camera=bpy.data.objects.new(data.name,data); scene.collection.objects.link(camera)
        camera.location=profile['location']; camera.rotation_euler=profile['rotation_euler']
        data.type=profile['projection']; data.ortho_scale=profile['ortho_scale']; data.lens=profile['focal_length']
        data.sensor_width=36; data.sensor_fit='HORIZONTAL'; data.shift_x=profile['shift_x']; data.shift_y=profile['shift_y']
        cameras[profile['view']]=camera
    return cameras


def regional_collision(mesh, selected_ids, baseline_vertices, margin):
    """Same weighted-region BVH method as existing collision tools; no empty PASS."""
    mesh.data.calc_loop_triangles()
    triangles=np.asarray([tuple(t.vertices) for t in mesh.data.loop_triangles],dtype=int)
    selected=np.zeros(len(mesh.data.vertices),dtype=bool); selected[list(selected_ids)]=True
    leg_indices=np.flatnonzero(selected[triangles].sum(axis=1)>=2)
    lo=baseline_vertices[list(selected_ids)].min(axis=0)-margin
    hi=baseline_vertices[list(selected_ids)].max(axis=0)+margin
    tri_points=baseline_vertices[triangles]
    nearby=np.all(tri_points.max(axis=1)>=lo,axis=1)&np.all(tri_points.min(axis=1)<=hi,axis=1)
    other_indices=np.flatnonzero(nearby & (selected[triangles].sum(axis=1)<2))
    if not len(leg_indices) or not len(other_indices):
        raise ValueError('Collision region has no triangles; refusing an empty PASS.')
    leg=[tuple(triangles[i]) for i in leg_indices]; other=[tuple(triangles[i]) for i in other_indices]
    def check(vertices):
        if len(vertices)!=len(selected): raise ValueError('Evaluated topology changed; collision mapping invalid')
        points=[Vector(v) for v in vertices]
        a=BVHTree.FromPolygons(points,leg,all_triangles=True)
        b=BVHTree.FromPolygons(points,other,all_triangles=True)
        hits=set()
        for i,j in a.overlap(b):
            if not set(leg[i]).intersection(other[j]): hits.add((int(leg_indices[i]),int(other_indices[j])))
        for i,j in a.overlap(a):
            if i<j and not set(leg[i]).intersection(leg[j]): hits.add((int(leg_indices[i]),int(leg_indices[j])))
        return hits
    return check, {'selected_triangles':len(leg),'nearby_other_triangles':len(other),
                   'method':'evaluated weighted region BVH, shared-vertex connections excluded',
                   'scope':'one changed chain and nearby mesh; not full-cycle collision certification'}


def run_iteration(output):
    output=Path(output).resolve(); request=json.loads((output/'request.json').read_text())
    manifest=request['manifest']; source=Path(manifest['best_validated_animation'])
    source_hash=file_hash(source)
    bpy.ops.wm.open_mainfile(filepath=str(source))
    scene=bpy.context.scene; arm,mesh=walk.bind_creature(scene)
    profile=walk.resolve_profile(arm,request.get('rig_profile') or None)
    original_action=arm.animation_data.action
    if original_action is None: raise ValueError('Best animation has no active Action')
    original_action.use_fake_user=True
    profiles=json.loads(Path(manifest['camera_profiles']).read_text())['profiles']
    cameras=render_setup(scene,mesh,profiles)
    if 'side' not in cameras: raise ValueError('Side calibration missing')
    scene.frame_set(scene.frame_start); bpy.context.view_layer.update()
    def hip_center():
        return sum((arm.matrix_world@arm.pose.bones[names[0]].head for names in profile['chains'].values()),Vector())/len(profile['chains'])
    root_start=hip_center(); camera_starts={view:camera.location.copy() for view,camera in cameras.items()}
    ground_obj=scene.objects.get('CMAI_Ground_Contact')
    ground=float(ground_obj.matrix_world.translation.z) if ground_obj else None
    ground_reference={'object':'CMAI_Ground_Contact','z':ground} if ground_obj else {'status':'MISSING'}
    # Recover this build's recorded contact height; never infer it from a moving foot.
    saved_ground=source.parent/'standing/standing_validation.json'
    visible_ground=scene.objects.get('CMAI_Walk_Ground')
    if ground is None and saved_ground.is_file() and visible_ground:
        saved=json.loads(saved_ground.read_text())
        z=float(saved['ground']); offset=z-float(visible_ground.matrix_world.translation.z)
        if saved.get('status')=='PASS' and abs(offset)<=.001:
            ground=z; ground_reference={'source_report':str(saved_ground),'z':z,
                'display_plane':visible_ground.name,'display_offset':offset,'status':'RECOVERED_SAVED_CONTACT_REFERENCE'}
    start_anatomy=walk.capture_anatomy(arm,mesh,profile)
    def render(name):
        travel=hip_center()-root_start; travel.z=0
        for view,camera in cameras.items():
            camera.location=camera_starts[view]+travel
            scene.camera=camera; scene.render.filepath=str(output/f'{name}_{view}.png')
            bpy.ops.render.render(write_still=True)
    # A sparse pose search, not a claim of video/Blender synchronization.
    frames=sorted(set(int(f) for f in np.linspace(scene.frame_start,min(scene.frame_end,120),8)))
    samples=[]
    for frame in frames:
        scene.frame_set(frame); bpy.context.view_layer.update()
        render('phase_'+str(frame))
        current_vertices=walk.mesh_world(mesh)
        lifted_names=[leg for leg,x in start_anatomy['legs'].items()
                      if ground is not None and current_vertices[x['indices'],2].min()-ground>.006]
        samples.append({'frame':frame,'lifted_legs':lifted_names})
    # External scorer selects the phase from actual rendered masks.
    (output/'phase_samples.json').write_text(json.dumps({'samples':samples,'source':str(source)},indent=2))
    import subprocess
    root=Path(__file__).resolve().parents[1]
    python=request['python']
    subprocess.run([python,'-m','creature_motion_ai.pose_comparison',str(output),'phase'],cwd=root,check=True)
    selection=json.loads((output/'phase_selection.json').read_text())
    adjustment=selection['framing_adjustment']
    cameras['side'].data.shift_x-=adjustment['dx_px']/640
    cameras['side'].data.shift_y+=adjustment['dy_px']/640
    frame=selection['selected_frame']; scene.frame_set(frame); bpy.context.view_layer.update()
    anatomy=walk.capture_anatomy(arm,mesh,profile); setups,_=walk.runtime(anatomy)
    near=sorted(setups,key=lambda leg:(setups[leg]['points'][1]-cameras['side'].location).length)
    lifted=[leg for leg in near if ground is not None and setups[leg]['sole']-ground>.006]
    selected_leg=(lifted or near)[0]; setup=setups[selected_leg]
    walk.isolate_evaluated_pose(arm)
    baseline={p.name:p.matrix_basis.copy() for p in arm.pose.bones}
    vertices=walk.mesh_world(mesh)
    groups={mesh.vertex_groups[name].index for name in setup['names'] if mesh.vertex_groups.get(name)}
    ids={v.index for v in mesh.data.vertices if sum(g.weight for g in v.groups if g.group in groups)>=.35}
    if len(ids)<10: raise ValueError('Insufficient weighted vertices for selected chain')
    step=.02*sum(setup['lengths'])
    checker,coverage=regional_collision(mesh,ids,vertices,max(.02,step*3))
    baseline_hits=checker(vertices)
    apply=walk.make_chain_applicator(arm,setups)
    horizontal=cameras['side'].rotation_euler.to_matrix()@Vector((1,0,0)); horizontal.z=0; horizontal.normalize()
    # Grounded feet stay fixed. Only already-lifted legs can change position.
    eligible=bool(lifted)
    deltas=[Vector((0,0,0)),step*horizontal, -step*horizontal,Vector((0,0,step))] if eligible else [Vector((0,0,0))]
    rows=[]
    for index,delta in enumerate(deltas):
        for p in arm.pose.bones: p.matrix_basis=baseline[p.name]
        bpy.context.view_layer.update()
        result={'status':'BASELINE'} if index==0 else apply(selected_leg,setup['points'][2]+delta,0)
        after=walk.mesh_world(mesh); hits=checker(after)
        contacts={leg:float(after[x['indices'],2].min()-ground) if ground is not None else None for leg,x in setups.items()}
        contact_preserved=ground is not None and all(abs(contacts[leg]-(x['sole']-ground))<.001 for leg,x in setups.items() if x['sole']-ground<=.004)
        penetration=max([max(0,-v) for v in contacts.values() if v is not None],default=None)
        bend={leg:float((arm.matrix_world@arm.pose.bones[x['names'][1]].head-arm.matrix_world@arm.pose.bones[x['names'][0]].head).cross(arm.matrix_world@arm.pose.bones[x['names'][2]].head-arm.matrix_world@arm.pose.bones[x['names'][0]].head).normalized().dot(x['normal'])) for leg,x in setups.items()}
        row={'candidate':index,'blender_frame':frame,'chain':selected_leg,'reference_leg_identity':'UNVERIFIED',
             'delta_world':list(delta),'solver':result,'knee_bend_dots':bend,
             'ground_clearance':contacts,'max_penetration':penetration,'contact_preserved':contact_preserved,
             'collision':dict(coverage,overlap_count=len(hits),new_overlaps=len(hits-baseline_hits),baseline_overlaps=len(baseline_hits)),
             'max_mesh_displacement':float(np.linalg.norm(after-vertices,axis=1).max()),
             'mechanical_pass':bool(index>0 and result['status']=='PASS' and min(bend.values())>0 and penetration is not None and penetration<=.003 and contact_preserved and not (hits-baseline_hits) and len(hits)<=len(baseline_hits))}
        render('candidate_'+str(index))
        scene.display.shading.light='STUDIO'; scene.display.shading.single_color=(.5,.62,.7)
        render('candidate_'+str(index)+'_surface')
        scene.display.shading.light='FLAT'; scene.display.shading.single_color=(1,1,1)
        if index>0:
            # Duplicate Action only. No full-cycle acceptance follows this single-pose test.
            action=original_action.copy(); action.name=original_action.name+'_PoseHypothesis_'+str(index)
            arm.animation_data.action=action
            if hasattr(action,'slots') and len(action.slots): arm.animation_data.action_slot=action.slots[0]
            for name in setup['names']:
                bone=arm.pose.bones[name]; bone.rotation_mode='QUATERNION'
                bone.keyframe_insert('rotation_quaternion',frame=frame,group=name)
            # Prove that Action evaluation reproduces what was measured/rendered.
            scene.frame_set(frame+1); scene.frame_set(frame); bpy.context.view_layer.update()
            replay=walk.mesh_world(mesh)
            replay_error=float(np.linalg.norm(replay-after,axis=1).max())
            row['action_replay']={'max_mesh_error':replay_error,'tolerance':.0001,
                                  'status':'PASS' if replay_error<.0001 else 'FAIL'}
            row['mechanical_pass']=row['mechanical_pass'] and replay_error<.0001
            row['diagnostic_blend']=str(output/f'candidate_{index}.blend')
            bpy.ops.wm.save_as_mainfile(filepath=row['diagnostic_blend'],copy=True)
            arm.animation_data.action=None
        rows.append(row)
    assert file_hash(source)==source_hash,'Source file changed unexpectedly'
    (output/'pose_candidates.json').write_text(json.dumps({'source':str(source),'source_sha256':source_hash,
        'source_unchanged':True,'original_action':original_action.name,'reference_frame':request['reference_frame'],
        'reference_selection':request.get('reference_selection'),
        'selected_blender_frame':frame,'selected_chain':selected_leg,'ground_reference':ground_reference,
        'camera_motion':'Follow XY root travel in diagnostic copy; saved calibration unchanged',
        'camera_framing_adjustment':adjustment,
        'candidates':rows,'notes':['Single-pose hypotheses only; not a synchronized motion reconstruction.',
        'Unidentified video legs remain UNVERIFIED. No measured joint positions assigned.',
        'Saved duplicate Actions have not passed loop/intermediate-frame tests.']},indent=2))
