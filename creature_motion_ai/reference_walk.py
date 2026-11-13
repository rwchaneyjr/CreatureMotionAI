"""Scene-safe standing-fit and walk services used by the sidebar.

Profiles contain creature-specific choices; all geometry comes from evaluated
Blender bones and the existing rest-relative solver. External IK libraries are
not installed into Blender and their existing adapters remain unchanged.
"""
import json
import math
import uuid
import hashlib
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector, Quaternion

from . import ik_step, rig_profiles, collision_proxies
from .walk_waypoints import mesh_world, fingerprint, create_walk, action_curves


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2), encoding='utf-8')


def motion_signature(scene,arm):
    """Detect edited curves/camera/constraints after a validation PASS."""
    payload=[]
    for obj in [arm,scene.camera]:
        if obj is None: payload.append(None); continue
        action=obj.animation_data.action if obj.animation_data else None
        curves=[]
        if action:
            for c in action_curves(action):
                curves.append([c.data_path,c.array_index,
                    [[list(k.co),list(k.handle_left),list(k.handle_right),k.interpolation] for k in c.keyframe_points],
                    [[m.type,getattr(m,'mode_before',None),getattr(m,'mode_after',None)] for m in c.modifiers]])
        animation=obj.animation_data
        payload.append([obj.name,action.name if action else None,curves,
            animation.action_slot.identifier if animation and animation.action_slot else None,
            [(track.name,track.mute,track.is_solo) for track in animation.nla_tracks] if animation else [],
            [(driver.data_path,driver.mute) for driver in animation.drivers] if animation else []])
    payload.append([[list(r) for r in arm.matrix_world],[(p.name,[(c.name,c.mute,c.influence) for c in p.constraints]) for p in arm.pose.bones]])
    if scene.camera:
        camera=scene.camera
        # Location may be animated: hash its curves above, not its current sample.
        payload.append([camera.data.type,camera.data.ortho_scale,camera.data.lens,
            list(camera.rotation_euler),list(camera.scale),
            list(camera.location) if not camera.animation_data else None,
            scene.render.resolution_x,scene.render.resolution_y,scene.render.resolution_percentage])
    return hashlib.sha256(json.dumps(payload).encode()).hexdigest()


def bind_creature(scene, preferred=None):
    arm=preferred if preferred and preferred.type=='ARMATURE' and preferred.name in scene.objects else None
    if arm is None:
        candidates=[o for o in scene.objects if o.type=='ARMATURE']
        if len(candidates)!=1:
            raise ValueError('Select the intended armature; the scene has multiple or no rigs.')
        arm=candidates[0]
    meshes=[o for o in scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==arm for m in o.modifiers)]
    if len(meshes)!=1:
        raise ValueError('This first builder supports one skinned mesh per rig. Join a diagnostic copy or provide a supported single-mesh rig.')
    return arm,meshes[0]


def resolve_profile(arm, path=None):
    profile=json.loads(Path(path).read_text()) if path else {}
    if not profile.get('chains'):
        proposed=rig_profiles.profile_from_bones([b.name for b in arm.data.bones],name=arm.name)
        profile['chains']={c.name.removeprefix('Leg_'):list(c.bones) for c in proposed.legs}
    chains=profile['chains']
    if len(chains)<2:
        raise ValueError('Leg naming is not recognized. Supply a rig-profile JSON with explicit three-bone chains; no anatomy will be guessed.')
    used=set()
    for leg,names in chains.items():
        if len(names)!=3 or any(n not in arm.pose.bones for n in names):
            raise ValueError(f'{leg}: three existing bones are required in the profile.')
        if used.intersection(names): raise ValueError('A bone belongs to multiple leg chains.')
        used.update(names)
        for first,second in zip(names,names[1:]):
            a,b=arm.data.bones[first],arm.data.bones[second]
            if b.parent!=a or (b.head_local-a.tail_local).length>1e-5:
                raise ValueError(f'{leg}: {second} must start at its parent tail; offset chains need a separate adapter.')
    roots=[b.name for b in arm.data.bones if b.parent is None]
    profile.setdefault('root_bone',roots[0] if len(roots)==1 else '')
    if profile['root_bone'] not in arm.pose.bones or arm.pose.bones[profile['root_bone']].parent:
        raise ValueError('Specify an existing top-level root bone in the profile.')
    for leg,names in chains.items():
        if profile['root_bone'] not in {p.name for p in arm.pose.bones[names[0]].parent_recursive}:
            raise ValueError(f'{leg} is not descended from the configured common root.')
    profile.setdefault('forward_world',[0,-1,0])
    profile.setdefault('phase_offsets',{leg:i/len(chains) for i,leg in enumerate(chains)})
    profile.setdefault('phase_evidence','Modeled staggered phases; reference leg identities NOT VERIFIED.')
    if set(profile['phase_offsets'])!=set(chains): raise ValueError('Phase offsets must contain exactly the configured legs.')
    return profile


def capture_anatomy(arm,mesh,profile):
    bpy.context.view_layer.update(); verts=mesh_world(mesh)
    result={'schema_version':1,'armature':arm.name,'mesh':mesh.name,'profile':profile,
            'geometry_sha256':fingerprint(arm,mesh),'bone_count':len(arm.data.bones),
            'baseline':{p.name:[list(r) for r in p.matrix] for p in arm.pose.bones},'legs':{}}
    for leg,names in profile['chains'].items():
        ps=[arm.pose.bones[n] for n in names]
        points=[arm.matrix_world@p.head for p in ps]+[arm.matrix_world@ps[-1].tail]
        matrices=[arm.matrix_world@p.matrix for p in ps]
        normal=(points[1]-points[0]).cross(points[2]-points[0])
        if normal.length<1e-8: raise ValueError(f'{leg}: standing chain is straight; load a naturally bent baseline before analysis.')
        group=mesh.vertex_groups.get(names[-1])
        if group is None: raise ValueError(f'{leg}: terminal bone has no vertex weights.')
        direction=(points[3]-points[2]).normalized(); length=(points[3]-points[2]).length
        ids=[v.index for v in mesh.data.vertices if any(g.group==group.index and g.weight>=.35 for g in v.groups)
             and (Vector(verts[v.index])-points[2]).dot(direction)>.15*length]
        if len(ids)<10: raise ValueError(f'{leg}: insufficient terminal-weighted foot vertices.')
        bones=[]
        for p,m in zip(ps,matrices):
            axis=m.to_3x3().inverted()@normal.normalized()
            bones.append({'name':p.name,'parent':p.parent.name if p.parent else None,
                'matrix_local':[list(r) for r in p.bone.matrix_local],
                'parent_relative_rest':[list(r) for r in (p.parent.bone.matrix_local.inverted()@p.bone.matrix_local if p.parent else p.bone.matrix_local)],
                'evaluated_world':[list(r) for r in m],'bend_axis_bone_local':list(axis.normalized()),
                'inherit_scale':p.bone.inherit_scale,
                'external_solver_axis':profile.get('solver_axes',{}).get(p.name),
                'external_solver_mapping_status':'NOT TESTED'})
        result['legs'][leg]={'names':names,'points':[list(p) for p in points],
            'matrices':[[list(r) for r in m] for m in matrices],'indices':ids,
            'lengths':[(points[i+1]-points[i]).length for i in range(3)],
            'normal':list(normal.normalized()),'sole':float(verts[ids,2].min()),'bones':bones}
    result['ground']=min(x['sole'] for x in result['legs'].values())
    return result


def runtime(anatomy):
    setups={}
    for leg,x in anatomy['legs'].items():
        setups[leg]={**x,'points':[Vector(p) for p in x['points']],
                     'matrices':[Matrix(m) for m in x['matrices']],
                     'indices':np.array(x['indices']),'normal':Vector(x['normal'])}
    return setups,{n:Matrix(m) for n,m in anatomy['baseline'].items()}


def isolate_evaluated_pose(arm):
    """Freeze what Blender actually evaluates, before disabling competing inputs."""
    matrices={p.name:p.matrix.copy() for p in arm.pose.bones}
    arm.animation_data_create()
    if arm.animation_data.action: arm.animation_data.action.use_fake_user=True
    arm.animation_data.action=None
    for track in arm.animation_data.nla_tracks: track.mute=True
    for driver in arm.animation_data.drivers: driver.mute=True
    for p in arm.pose.bones:
        for constraint in p.constraints: constraint.mute=True
    bpy.context.view_layer.update()
    for p in sorted(arm.pose.bones,key=lambda p:len(p.parent_recursive)):
        p.matrix=matrices[p.name]; p.rotation_mode='QUATERNION'; bpy.context.view_layer.update()


def apply_local_joint_delta(arm,bone_name,axis_bone_local,angle,baseline_basis):
    """Explicit per-bone rest-basis rotation; never interpret a world X as local X.

    External Pinocchio adapters must supply the axis in this declared basis and
    verify their predicted joints. This function does not assume that mapping.
    """
    p=arm.pose.bones[bone_name]; axis=Vector(axis_bone_local)
    if axis.length<1e-8: raise ValueError('Joint axis is zero')
    basis=baseline_basis.copy(); location,rotation,scale=basis.decompose()
    basis=Matrix.LocRotScale(location,Quaternion(axis.normalized(),angle)@rotation,scale)
    kwargs={'parent_matrix':p.parent.matrix,'parent_matrix_local':p.parent.bone.matrix_local} if p.parent else {}
    expected=p.bone.convert_local_to_pose(basis,p.bone.matrix_local,**kwargs)
    p.matrix_basis=basis; bpy.context.view_layer.update()
    return expected


def validate_local_axes(arm,anatomy):
    basis={p.name:p.matrix_basis.copy() for p in arm.pose.bones}; rows=[]
    try:
        for leg,x in anatomy['legs'].items():
            for bone in x['bones']:
                for angle in [-.1,.1]:
                    for p in arm.pose.bones: p.matrix_basis=basis[p.name]
                    bpy.context.view_layer.update()
                    p=arm.pose.bones[bone['name']]
                    expected=apply_local_joint_delta(arm,p.name,bone['bend_axis_bone_local'],angle,basis[p.name])
                    expected_head=arm.matrix_world@expected.translation
                    expected_tail=arm.matrix_world@(expected@Vector((0,p.bone.length,0)))
                    error=max((arm.matrix_world@p.head-expected_head).length,(arm.matrix_world@p.tail-expected_tail).length)
                    rows.append({'leg':leg,'bone':p.name,'angle':angle,'head_tail_error':error,'status':'PASS' if error<1e-4 else 'FAIL'})
    finally:
        for p in arm.pose.bones: p.matrix_basis=basis[p.name]
        bpy.context.view_layer.update()
    if any(x['status']=='FAIL' for x in rows): raise ValueError('Per-bone local-axis evaluation failed.')
    return rows


def make_chain_applicator(arm,setups,min_flex=8,max_flex=135):
    inverse=arm.matrix_world.inverted()
    def apply(leg,target,lift):
        x=setups[leg]; hip=x['points'][0]+Vector((0,0,lift))
        old=(x['points'][2]-x['points'][0]).normalized(); direction=(target-hip).normalized()
        normal=old.rotation_difference(direction)@x['normal']
        solution=ik_step.solve_rest_relative_two_link(hip,target,*x['lengths'][:2],normal,min_knee_angle=math.radians(min_flex))
        if solution['status']!='PASS': return {'status':'FAIL','reason':solution['reason']}
        flex=180-math.degrees(solution['knee_angle'])
        if flex>max_flex: return {'status':'FAIL','reason':'knee_flexion_limit','knee_flexion_deg':flex}
        knee=solution['knee']
        for i,(head,tail) in enumerate([(hip,knee),(knee,target)]):
            matrix=ik_step.world_direction_pose_matrix(x['matrices'][i],x['points'][i],head,tail,x['points'][i+1])
            arm.pose.bones[x['names'][i]].matrix=inverse@matrix
            bpy.context.view_layer.update()
        ik_step.restore_terminal_foot_world_orientation(arm,x['names'][2],x['matrices'][2],target)
        bpy.context.view_layer.update()
        actual=[arm.matrix_world@arm.pose.bones[n].head for n in x['names']]+[arm.matrix_world@arm.pose.bones[x['names'][-1]].tail]
        expected=[hip,knee,target,target+x['points'][3]-x['points'][2]]
        error=max((a-b).length for a,b in zip(actual,expected))
        return {'status':'PASS' if error<1e-4 else 'FAIL','joint_error':error,'knee_flexion_deg':flex,
            'bend_dot':(actual[1]-actual[0]).cross(actual[2]-actual[0]).normalized().dot(normal),
            'length_error':max(abs((actual[i+1]-actual[i]).length-x['lengths'][i]) for i in range(3)),
            'foot_angle_deg':math.degrees((arm.matrix_world@arm.pose.bones[x['names'][2]].matrix).to_quaternion().rotation_difference(x['matrices'][2].to_quaternion()).angle),
            'foot_world':list(actual[-1])}
    return apply


def fit_standing(scene,arm,mesh,anatomy,settings,out):
    setups,baseline=runtime(anatomy); profile=anatomy['profile']; root=profile['root_bone']
    isolate_evaluated_pose(arm); axis_tests=validate_local_axes(arm,anatomy)
    apply=make_chain_applicator(arm,setups,settings['minimum_knee_flexion_degrees'],settings['maximum_knee_flexion_degrees'])
    inverse=arm.matrix_world.inverted(); lift=settings['body_height']; ground=anatomy['ground']
    matrix=arm.matrix_world@baseline[root]; matrix.translation+=Vector((0,0,lift)); arm.pose.bones[root].matrix=inverse@matrix
    bpy.context.view_layer.update(); targets={}
    for leg,x in setups.items():
        hip=x['points'][0]; target=hip+(x['points'][2]-hip)*settings['inward']
        target.z=x['points'][2].z+ground-x['sole']
        target+=Vector(profile.get('stance_offsets',{}).get(leg,[0,0,0])); targets[leg]=target
    for iteration in range(8):
        rows={leg:apply(leg,target,lift) for leg,target in targets.items()}
        if any(r['status']!='PASS' for r in rows.values()):
            write_json(out/'standing_failure.json',rows); raise ValueError('Standing target unreachable; reduce Body height or change foot placement in the profile.')
        vertices=mesh_world(mesh); errors={leg:float(vertices[x['indices'],2].min()-ground) for leg,x in setups.items()}
        if max(abs(e) for e in errors.values())<.00025: break
        for leg,error in errors.items(): targets[leg].z-=error*.9
    for leg in rows: rows[leg]['sole_error']=errors[leg]
    if max(abs(e) for e in errors.values())>.003:
        write_json(out/'standing_failure.json',rows)
        raise ValueError('Standing mesh contacts did not converge; see standing_failure.json.')
    action=bpy.data.actions.new('CMAI_Standing_'+out.name); action.use_fake_user=True; arm.animation_data.action=action
    for p in arm.pose.bones:
        for channel in ['location','rotation_quaternion','scale']: p.keyframe_insert(channel,frame=1)
    scene.frame_set(1); bpy.context.view_layer.update()
    report={'status':'PASS','visual_status':'NOT TESTED','ground':ground,'body_lift':lift,'legs':rows,
            'axis_tests':axis_tests,'geometry_preserved':fingerprint(arm,mesh)==anatomy['geometry_sha256'],
            'targets':{k:list(v) for k,v in targets.items()},'action':action.name}
    write_json(out/'standing_validation.json',report)
    return report


def generate_waypoints_or_walk(scene,arm,mesh,anatomy,standing,settings,out,plan_only=False,prepared=None):
    setups,baseline=runtime(anatomy)
    vertices=mesh_world(mesh); edges=np.empty(len(mesh.data.edges)*2,dtype=np.int32)
    mesh.data.edges.foreach_get('vertices',edges); edges=edges.reshape(-1,2)
    lengths=np.linalg.norm(vertices[edges[:,0]]-vertices[edges[:,1]],axis=1)
    selected=(standing['body_lift'],{k:Vector(v) for k,v in standing['targets'].items()},standing['legs'])
    apply=make_chain_applicator(arm,setups,settings['minimum_knee_flexion_degrees'],settings['maximum_knee_flexion_degrees'])
    return create_walk(scene,arm,mesh,out,standing,setups,selected,baseline,apply,standing['ground'],edges,lengths,
                       overrides=settings,root_name=anatomy['profile']['root_bone'],plan_only=plan_only,prepared=prepared)


def setup_preview_camera(scene,mesh,forward,ground):
    """Create an approximate side camera. This does NOT certify calibration."""
    verts=mesh_world(mesh); low=verts.min(0); high=verts.max(0); center=Vector((low+high)*.5)
    forward=Vector(forward).normalized(); side=Vector((0,0,1)).cross(forward)
    size=float(np.linalg.norm(high-low)); data=bpy.data.cameras.new('CMAI_Walk_Side')
    camera=bpy.data.objects.new('CMAI_Walk_Side',data); scene.collection.objects.link(camera)
    camera.location=center-side*size*4+forward*size*.25+Vector((0,0,size*.325))
    camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler(); data.type='ORTHO'
    data.ortho_scale=max(size*1.10,(high[2]-low[2])*2.1); scene.camera=camera
    scene.render.resolution_x=1280; scene.render.resolution_y=720; scene.render.resolution_percentage=100
    for obj in scene.objects:
        if obj.type in {'LIGHT','CAMERA'} and obj!=camera: obj.hide_render=True
    bpy.ops.mesh.primitive_plane_add(size=max(200,size*100),location=(0,0,ground-.0002))
    plane=bpy.context.object; plane.name='CMAI_Walk_Ground'
    material=bpy.data.materials.new('CMAI_Walk_Ground'); material.diffuse_color=(.7,.72,.75,1); plane.data.materials.append(material)
    scene.world=bpy.data.worlds.new('CMAI_Walk_World'); scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.7,.75,.8,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.5
    for name,offset,power in [('Key',(-2,-2,3),450),('Fill',(2,-1,2),250)]:
        light=bpy.data.lights.new('CMAI_Walk_'+name,'AREA'); light.energy=power; light.shape='DISK'; light.size=3
        obj=bpy.data.objects.new(light.name,light); scene.collection.objects.link(obj); obj.location=Vector(offset)
        obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler()
    scene.render.engine='BLENDER_EEVEE'; scene.eevee.taa_render_samples=32
    scene.view_settings.view_transform='AgX'; scene.render.film_transparent=False
    return {'status':'NOT TESTED','camera':camera.name,'orthographic_scale':data.ortho_scale,
            'message':'Automatic framing only; independent reference calibration is incomplete.'}


def validate_animation(scene,arm,mesh,anatomy,settings,ground,out):
    """Measure actual saved-Action evaluation through the entire preview."""
    from bpy_extras.object_utils import world_to_camera_view
    setups,_=runtime(anatomy); root=anatomy['profile']['root_bone']; cycle=settings['cycle_frames']
    rows=[]; previous={}; slips={k:[] for k in setups}; first_mesh=None; first_joints=None
    action=arm.animation_data.action if arm.animation_data else None
    if action is None: raise ValueError('No active Action is assigned to the working armature.')
    for f in range(1,122):
        scene.frame_set(f); bpy.context.view_layer.update(); vertices=mesh_world(mesh)
        root_position=arm.matrix_world@arm.pose.bones[root].head
        relative=vertices-np.array(root_position)
        if first_mesh is None: first_mesh=relative.copy()
        frame={'frame':f,'legs':{},'camera_outside_vertices':0}
        for leg,x in setups.items():
            pts=[arm.matrix_world@arm.pose.bones[n].head for n in x['names']]+[arm.matrix_world@arm.pose.bones[x['names'][-1]].tail]
            d=(pts[2]-pts[0]).normalized(); old=(x['points'][2]-x['points'][0]).normalized()
            bend=(pts[1]-pts[0]).cross(pts[2]-pts[0]).normalized().dot(old.rotation_difference(d)@x['normal'])
            contact=((f-1)/cycle+settings['phase_offsets'][leg])%1<=settings['duty_factor']
            vv=vertices[x['indices']]
            if leg in previous and contact and previous[leg][0]:
                slips[leg].append(float(np.linalg.norm(vv[:,:2]-previous[leg][1],axis=1).max()))
            previous[leg]=(contact,vv[:,:2].copy())
            frame['legs'][leg]={'clearance':float(vv[:,2].min()-ground),'contact':contact,'bend_dot':bend,
                'mesh_movement_relative_to_body':float(np.linalg.norm(relative[x['indices']]-first_mesh[x['indices']],axis=1).max()),
                'bone_length_error':max(abs((pts[i+1]-pts[i]).length-x['lengths'][i]) for i in range(3))}
        segments=collision_proxies.segments_for_chains(arm,anatomy['profile']['chains'],anatomy['profile'].get('body_bones',[]))
        hits=[]
        for i,a in enumerate(segments):
            for b in segments[i+1:]:
                if a['region']==b['region']: continue
                overlap=a['r']+b['r']-collision_proxies._segdist(a['a'],a['b'],b['a'],b['b'])
                if overlap>0: hits.append({'a':a['bone'],'b':b['bone'],'overlap':overlap})
        frame['proxy_collisions']=hits
        if scene.camera:
            # All vertices at selected extremes, not just a possibly misleading origin.
            if f in [1,11,21,31,61,91,120]:
                world_to_camera=scene.camera.matrix_world.inverted()
                cam=np.array(world_to_camera); camera_vertices=vertices@cam[:3,:3].T+cam[:3,3]
                corners=scene.camera.data.view_frame(scene=scene)
                xx=[c.x for c in corners]; yy=[c.y for c in corners]
                outside=(camera_vertices[:,0]<min(xx))|(camera_vertices[:,0]>max(xx))|(camera_vertices[:,1]<min(yy))|(camera_vertices[:,1]>max(yy))|(camera_vertices[:,2]>=0)
                frame['camera_outside_vertices']=int(outside.sum())
        else: frame['camera_outside_vertices']=len(vertices)
        rows.append(frame)
        if f%30==1: print('BUILDER VALIDATE',f,flush=True)
    summary={}
    for leg,x in setups.items():
        samples=[r['legs'][leg] for r in rows[:-1]]
        entry={'max_penetration':max(0,-min(r['clearance'] for r in samples)),
               'max_contact_float':max(0,max(r['clearance'] for r in samples if r['contact'])),
               'max_clearance':max(r['clearance'] for r in samples),
               'max_mesh_movement':max(r['mesh_movement_relative_to_body'] for r in samples),
               'min_bend_dot':min(r['bend_dot'] for r in samples),'max_length_error':max(r['bone_length_error'] for r in samples),
               'max_sole_slip':max(slips[leg],default=0)}
        entry['status']='PASS' if entry['max_penetration']<.003 and entry['max_contact_float']<.004 and entry['min_bend_dot']>.95 and entry['max_length_error']<1e-5 and entry['max_mesh_movement']>sum(x['lengths'])*.02 and entry['max_sole_slip']<settings.get('maximum_stance_slip',.003) else 'FAIL'
        summary[leg]=entry
    loop=float(np.linalg.norm(relative-first_mesh,axis=1).max())
    collisions=sum(len(f['proxy_collisions']) for f in rows)
    visible=not any(f['camera_outside_vertices'] for f in rows)
    preserved=fingerprint(arm,mesh)==anatomy['geometry_sha256']
    passed=all(x['status']=='PASS' for x in summary.values()) and loop<1e-5 and collisions==0 and visible and preserved
    result={'status':'PASS' if passed else 'FAIL','action':action.name,
            'slot':arm.animation_data.action_slot.identifier if arm.animation_data.action_slot else None,
            'legs':summary,'loop_mesh_relative_error':loop,'proxy_collision_samples':collisions,
            'camera_contains_creature':visible,'original_data_preserved':preserved,
            'exact_surface_collision':'NOT TESTED','natural_walking_visual_approval':'NOT TESTED',
            'mesh_stretch':'See waypoint walk_validation.json; numerical movement is not proof of acceptable deformation.',
            'frames':rows}
    result['motion_signature']=motion_signature(scene,arm)
    write_json(out/'animation_validation.json',result); scene.frame_set(1)
    return result
