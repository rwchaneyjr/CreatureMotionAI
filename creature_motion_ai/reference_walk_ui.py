"""Guided sidebar for the executed standing-fit/waypoint workflow."""
import json
import subprocess
import time
import uuid
from pathlib import Path

import bpy
from bpy.props import StringProperty, FloatProperty, IntProperty, PointerProperty, EnumProperty, BoolProperty
from . import reference_walk as service
from . import auto_anatomy
from . import video_rig_analysis
from . import loop_service

STAGES=[('rig','Analyze Creature Rig'),('video','Analyze Reference Video'),('camera','Calibrate Camera'),
        ('standing','Fit Standing Pose'),('standing_preview','Preview Standing Pose'),
        ('waypoints','Generate Walking Waypoints'),('walk','Build Eight-Leg Walk'),
        ('validation','Validate Animation'),('render','Render Five-Second Preview'),('export','Export Animation')]
PENDING={'video':'Automatic video analysis is not yet connected to this builder; existing tracking/review tools remain available.',
         'camera':'Automatic side framing is included. Independent reference camera calibration remains incomplete.',
         'export':'Final FBX export/reimport validation and visual-approval gating are not yet integrated.'}


def read_state(scene):
    try: return json.loads(scene.cmai_walk.state_json or '{}')
    except ValueError: return {}


def save_state(scene,state):
    scene.cmai_walk.state_json=json.dumps(state)
    if state.get('run'): service.write_json(Path(state['run'])/'workflow_state.json',state)


def changed_settings(self,context):
    # Old PASS labels must not survive parameter changes.
    state=read_state(context.scene) if context and hasattr(context.scene,'cmai_walk') else {}
    if state:
        for key,_ in STAGES:
            if key not in ('rig','video','camera'): state.setdefault('stages',{})[key]='NOT TESTED'
        state['message']='Settings changed. Refit standing and regenerate waypoints before building.'
        self.state_json=json.dumps(state)


def changed_profile(self,context):
    state=read_state(context.scene) if context and hasattr(context.scene,'cmai_walk') else {}
    if state:
        state['stages']={key:'NOT TESTED' for key,_ in STAGES}
        state['message']='Rig or profile changed. Analyze Creature Rig again before modifying poses.'
        self.state_json=json.dumps(state)


class CMAI_WalkSettings(bpy.types.PropertyGroup):
    rig: PointerProperty(name='Creature armature',type=bpy.types.Object,poll=lambda self,obj:obj.type=='ARMATURE',update=changed_profile)
    profile_path: StringProperty(name='Rig profile JSON',subtype='FILE_PATH',update=changed_profile)
    output: StringProperty(name='New outputs',subtype='DIR_PATH',default='//cmai_walk_outputs')
    external_python: StringProperty(name='OpenCV Python',subtype='FILE_PATH')
    body_height: FloatProperty(name='Body height adjustment',default=.05,min=-1,max=10,update=changed_settings)
    inward: FloatProperty(name='Ankle spread factor',default=.5,min=.1,max=1.5,update=changed_settings)
    stride: FloatProperty(name='Step length',default=.1,min=.001,max=10,update=changed_settings)
    lift_fraction: FloatProperty(name='Lift / upper+lower length',default=.2,min=.01,max=.6,update=changed_settings)
    cycle_frames: EnumProperty(name='Cycle / speed',items=[(str(n),f'{n} frames',f'{120//n} complete cycles in five seconds') for n in [20,24,30,40,60,120]],default='40',update=changed_settings)
    body_bob: FloatProperty(name='Body vertical shift',default=.003,min=0,max=1,update=changed_settings)
    phase_json: StringProperty(name='Per-leg phases JSON',default='{}',update=changed_settings)
    state_json: StringProperty(default='{}',options={'HIDDEN'})
    auto_report: StringProperty(name='Automatic anatomy report',subtype='FILE_PATH')
    auto_status: StringProperty(name='Automatic anatomy status',default='NOT TESTED')
    analysis_video: StringProperty(name='Reference video',subtype='FILE_PATH')
    analysis_status: StringProperty(name='Video + rig analysis',default='NOT TESTED')
    analysis_report: StringProperty(name='Combined analysis report',subtype='FILE_PATH')
    camera_search_status: StringProperty(name='Camera search',default='NOT TESTED')
    camera_profile: StringProperty(name='Camera profile',subtype='FILE_PATH')
    side_video: StringProperty(name='Side reference video',subtype='FILE_PATH')
    front_video: StringProperty(name='Front reference video',subtype='FILE_PATH')
    dual_camera_report: StringProperty(name='Dual camera report',subtype='FILE_PATH')
    camera_analysis_report: StringProperty(name='Reference camera analysis',subtype='FILE_PATH')
    loop_mode: EnumProperty(name='Loop mode', items=[('IN_PLACE','Walking in place','Remove root-object travel curves'),('TRAVELING','Forward travel','Preserve root travel')], default='IN_PLACE')
    loop_output: StringProperty(name='Loop output', subtype='DIR_PATH', default='//cmai_loop_outputs')
    loop_status: StringProperty(name='Loop status', default='NOT TESTED')
    loop_report: StringProperty(name='Loop report', subtype='FILE_PATH')
    compare_report: StringProperty(name='Compare & Improve report', subtype='FILE_PATH')
    compare_video: StringProperty(name='Before/after comparison video', subtype='FILE_PATH')
    standing_model: StringProperty(name='Standing baseline',subtype='FILE_PATH')
    best_animation: StringProperty(name='Preserved best animation',subtype='FILE_PATH')
    shared_manifest: StringProperty(name='Shared workflow manifest',subtype='FILE_PATH')
    project_folder: StringProperty(name='CreatureMotionAI project',subtype='DIR_PATH',default='C:/Users/rober/CreatureMotionAI')
    pose_reference_frame: IntProperty(name='Side pose frame',default=26,min=1)
    auto_reference_pose: BoolProperty(name='Select reliable side pose automatically',default=True)
    reference_pose_status: StringProperty(name='Reference pose result',default='NOT TESTED')
    solver_backend: EnumProperty(name='Solver', items=[('AUTO','Auto','Use Pinocchio only when movement conversion is validated; otherwise use the existing solver'),('EXISTING','Existing Solver','Use the current CreatureMotionAI solver'),('PINOCCHIO','Pinocchio','Request Pinocchio, with safe fallback if validation is unavailable')], default='AUTO', update=changed_settings)
    solver_status: StringProperty(name='Solver status', default='NOT TESTED')


def configuration(scene,profile):
    p=scene.cmai_walk
    config={**profile,'cycle_frames':int(p.cycle_frames),'body_height':p.body_height,'inward':p.inward,
        'shared_stride':p.stride,'lift_fraction':p.lift_fraction,'body_bob':p.body_bob,
        'world_planted_support':True,'contact_xy_tolerance':.0008,'fps':24,'solver_backend':p.solver_backend,
        'minimum_knee_flexion_degrees':profile.get('minimum_knee_flexion_degrees',8),
        'maximum_knee_flexion_degrees':profile.get('maximum_knee_flexion_degrees',135)}
    phases=json.loads(p.phase_json)
    if phases: config['phase_offsets']=phases
    if set(config['phase_offsets'])!=set(profile['chains']): raise ValueError('Per-leg phase names must match the rig profile.')
    if any(not 0<=float(v)<1 for v in config['phase_offsets'].values()): raise ValueError('Each phase offset must be in [0,1).')
    return config


def require(state,stage):
    if state.get('stages',{}).get(stage)!='PASS': raise ValueError(f'Complete {dict(STAGES)[stage]} first. Current status is not PASS.')


def new_output(state,label):
    out=Path(state['run'])/(label+'_'+uuid.uuid4().hex[:8]); out.mkdir()
    return out


def working_objects(scene,state):
    arm=scene.objects.get(state.get('working_armature','')); mesh=scene.objects.get(state.get('working_mesh',''))
    if arm is None or mesh is None: raise ValueError('Switch to the builder working scene or run Fit Standing Pose again.')
    return arm,mesh


def use_standing_action(scene,arm,state):
    action=bpy.data.actions.get(state['standing_action'])
    if action is None: raise ValueError('Standing Action was removed; refit standing.')
    arm.animation_data.action=action
    if action.slots: arm.animation_data.action_slot=action.slots[0]
    scene.frame_set(1); bpy.context.view_layer.update()


class CMAI_OT_walk_preset(bpy.types.Operator):
    bl_idname='cmai.walk_load_balisk_profile'; bl_label='Load Balisk Review Settings'
    def execute(self,context):
        path=Path(__file__).parent/'profiles/balisk_reference_walk.json'; profile=json.loads(path.read_text())
        p=context.scene.cmai_walk; p.profile_path=str(path)
        for prop,key in [('body_height','body_height'),('inward','inward'),('stride','shared_stride'),('lift_fraction','lift_fraction'),('body_bob','body_bob')]: setattr(p,prop,profile[key])
        p.cycle_frames=str(profile['cycle_frames']); p.phase_json=json.dumps(profile['phase_offsets'])
        if not p.external_python and bpy.data.filepath:
            for parent in Path(bpy.data.filepath).parents:
                candidate=parent/'.venv-dlc/Scripts/python.exe'
                if candidate.is_file(): p.external_python=str(candidate); break
        p.state_json='{}'
        self.report({'INFO'},'Balisk review settings loaded. Analyze the original natural standing rig next.')
        return {'FINISHED'}


class CMAI_OT_detect_creature(bpy.types.Operator):
    bl_idname='cmai.detect_creature_automatically'; bl_label='Detect Creature Automatically'
    bl_description='Propose limb chains from hierarchy and geometry; review is required'
    def execute(self, context):
        try:
            arm, mesh = service.bind_creature(context.scene, context.scene.cmai_walk.rig or context.active_object)
            roots=[b.name for b in arm.data.bones if b.parent is None]
            if len(roots)!=1: raise ValueError('Automatic detection needs one top-level root; use a profile for this rig.')
            report=auto_anatomy.detect_anatomy(arm); report['mesh']=mesh.name; report['root_bone']=roots[0]
            out=Path(bpy.path.abspath(context.scene.cmai_walk.output or '//cmai_walk_outputs'))
            out.mkdir(parents=True,exist_ok=True)
            target=out/('auto_anatomy_'+time.strftime('%Y%m%d_%H%M%S')+'.json')
            service.write_json(target,report)
            profile=auto_anatomy.profile_from_detection(report,roots[0])
            profile_path=target.with_name(target.stem+'_profile.json'); service.write_json(profile_path,profile)
            p=context.scene.cmai_walk; p.rig=arm; p.profile_path=str(profile_path); p.auto_report=str(target)
            p.auto_status=report['mapping_confidence']+' / REVIEW REQUIRED'
            self.report({'INFO'},f'Found {report["selected_leg_count"]} candidate chains; review the saved report.')
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'},str(exc)); return {'CANCELLED'}


class CMAI_OT_generate_auto_preview(bpy.types.Operator):
    bl_idname='cmai.generate_auto_walk_preview'; bl_label='Generate Walk Preview'
    def execute(self, context):
        p=context.scene.cmai_walk
        try:
            if not p.auto_report: raise ValueError('Run automatic detection first.')
            report=json.loads(Path(bpy.path.abspath(p.auto_report)).read_text())
            if not report.get('confirmed'):
                raise ValueError('Anatomy is unconfirmed. Review candidates and set confirmed=true before generating.')
            for stage in ('rig','standing','waypoints','walk','validation','render'):
                result=bpy.ops.cmai.reference_walk_step(stage=stage)
                if result != {'FINISHED'}: return result
            self.report({'INFO'},'Automatic walk preview generated after anatomy confirmation.')
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'},str(exc)); return {'CANCELLED'}


class CMAI_OT_analyze_video_rig(bpy.types.Operator):
    bl_idname='cmai.analyze_video_and_rig'; bl_label='Analyze Video + Rig'
    bl_description='Analyze reference motion and rig anatomy without creating an Action'
    def execute(self, context):
        p=context.scene.cmai_walk
        try:
            arm, mesh=service.bind_creature(context.scene, p.rig or context.active_object)
            primary = p.side_video or p.analysis_video
            if not primary: raise ValueError('Choose a Side Reference Video or Reference video first.')
            video=Path(bpy.path.abspath(primary))
            if not video.is_file(): raise ValueError(f'Reference video not found: {video}')
            out=Path(bpy.path.abspath(p.output or '//cmai_walk_outputs'))/'video_rig_analysis_'+time.strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:6]
            out.mkdir(parents=True,exist_ok=True)
            # Reuse the existing detector; this is a proposal, never an approval.
            roots=[b.name for b in arm.data.bones if b.parent is None]
            rig_report=auto_anatomy.detect_anatomy(arm); rig_report['mesh']=mesh.name; rig_report['root_bone']=roots[0] if len(roots)==1 else None
            rig_path=out/'anatomy_mapping.json'; service.write_json(rig_path,rig_report)
            manual=Path(bpy.path.abspath('//data/generated/frontL_selected_video_landmarks.json'))
            dlc=Path(bpy.path.abspath('//data/generated/selected_video_dlc_frontL_predictions.json'))
            # Run analysis in the configured external environment so the Blender
            # Python need not contain OpenCV. Side is primary; front is optional.
            py=Path(bpy.path.abspath(p.external_python)); tool=Path(__file__).parent.parent/'tools'/'analyze_video_rig.py'
            if not py.is_file(): raise ValueError('Select the external Python environment with OpenCV.')
            reports={}
            inputs=[('side',video)]
            if p.front_video:
                front=Path(bpy.path.abspath(p.front_video))
                if not front.is_file(): raise ValueError(f'Front reference video not found: {front}')
                inputs.append(('front',front))
            for label,source in inputs:
                target=out/label
                subprocess.run([str(py),str(tool),'--video',str(source),'--rig-report',str(rig_path),'--output',str(target),
                                '--manual',str(manual)] if manual.is_file() else
                               [str(py),str(tool),'--video',str(source),'--rig-report',str(rig_path),'--output',str(target)],
                               check=True,timeout=600,capture_output=True,text=True)
                reports[label]=json.loads((target/'video_rig_analysis.json').read_text())
            sync={'status':'NOT_ESTIMATED' if len(inputs)==2 else 'NOT_APPLICABLE',
                  'reason':'Independent videos require a measured temporal correspondence; matching FPS alone is insufficient.',
                  'combine_motion_measurements':False}
            combined={'status':'ANALYSIS_COMPLETE_REVIEW_REQUIRED','primary_view':'side','side':reports['side'],
                      'front':reports.get('front'),'synchronization':sync,
                      'motion_policy':{'primary_gait_source':'side','front_role':'optional_spacing_lateral_body_guidance','front_used_for_framewise_gait_fit':False,'walking_generation_blocked_by_sync':False},
                      'inputs':[str(v) for _,v in inputs],
                      'note':'Front video is optional and independently analyzed; no Action was created.'}
            service.write_json(out/'video_rig_analysis.json',combined)
            p.analysis_video=str(video); p.analysis_report=str(out/'video_rig_analysis.json'); p.analysis_status=combined['status']
            self.report({'INFO'},f'Analysis complete for {len(inputs)} video input(s); review {out / "video_rig_analysis.json"}. No Action was created.')
            return {'FINISHED'}
        except Exception as exc:
            p.analysis_status='FAIL'; self.report({'ERROR'},str(exc)); return {'CANCELLED'}

class CMAI_OT_estimate_dual_cameras(bpy.types.Operator):
    bl_idname='cmai.estimate_dual_reference_cameras'; bl_label='Estimate Side + Front Cameras'
    bl_description='Search independent camera candidates; synchronization is reported, not assumed'
    def execute(self, context):
        p=context.scene.cmai_walk
        try:
            if not p.side_video: raise ValueError('Choose a Side Reference Video first. The Front Reference Video is optional.')
            blend=Path(bpy.data.filepath)
            py=Path(bpy.path.abspath(p.external_python)); tool=Path(__file__).parent.parent/'tools'/'estimate_reference_camera.py'
            if not blend.is_file() or not py.is_file(): raise ValueError('Save the Blender file and select the external OpenCV Python.')
            root=Path(bpy.path.abspath(p.output or '//cmai_walk_outputs'))/('dual_camera_'+time.strftime('%Y%m%d_%H%M%S')); root.mkdir(parents=True,exist_ok=True)
            reports={}
            inputs=[('side',p.side_video)]
            if p.front_video: inputs.append(('front',p.front_video))
            for label,video in inputs:
                v=Path(bpy.path.abspath(video)); out=root/label
                subprocess.run([str(py),str(tool),'--blend',str(blend),'--video',str(v),'--blender',bpy.app.binary_path,'--output',str(out)],check=True,timeout=900)
                reports[label]=json.loads((out/'camera_search_report.json').read_text())
            combined={'status':'SIDE_CAMERA_SEARCH_COMPLETE_REVIEW_REQUIRED' if len(inputs)==1 else 'DUAL_CAMERA_SEARCH_COMPLETE_REVIEW_REQUIRED','side':reports['side'],'front':reports.get('front'),'synchronization':{'status':'NOT_TESTED' if len(inputs)==2 else 'NOT_APPLICABLE','reason':'Independent videos are never combined frame-by-frame without verified timing and limb identity.','combine_motion_measurements':False},'camera_objects':['CMAI_Side_Camera'] + (['CMAI_Front_Camera'] if len(inputs)==2 else []),'primary_view':'side','front_view_role':'optional secondary lateral-spacing and visual validation'}
            for name in ('CMAI_Side_Camera','CMAI_Front_Camera'):
                if not bpy.data.objects.get(name):
                    data=bpy.data.cameras.new(name); obj=bpy.data.objects.new(name,data); context.scene.collection.objects.link(obj); data.type='ORTHO'
            target=root/'camera_profiles_report.json'; service.write_json(target,combined); p.dual_camera_report=str(target); self.report({'INFO'},f'Independent camera profile(s) saved in {root}; side motion remains usable without synchronization.')
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'},str(exc)); return {'CANCELLED'}

class CMAI_OT_analyze_reference_camera(bpy.types.Operator):
    bl_idname='cmai.analyze_reference_camera'; bl_label='Analyze Reference Camera'
    def execute(self, context):
        p=context.scene.cmai_walk
        try:
            video=Path(bpy.path.abspath(p.side_video or p.analysis_video))
            py=Path(bpy.path.abspath(p.external_python)); tool=Path(__file__).parent.parent/'tools'/'analyze_reference_camera.py'
            if not video.is_file() or not py.is_file(): raise ValueError('Choose a reference video and external OpenCV Python.')
            out=Path(bpy.path.abspath(p.output or '//cmai_walk_outputs'))/'reference_camera_'+time.strftime('%Y%m%d_%H%M%S'); out.mkdir(parents=True,exist_ok=True)
            subprocess.run([str(py),str(tool),'--video',str(video),'--output',str(out/'reference_camera_analysis.json')],check=True,timeout=180)
            p.camera_analysis_report=str(out/'reference_camera_analysis.json'); self.report({'INFO'},'Reference camera analyzed; projection remains reviewable.')
            return {'FINISHED'}
        except Exception as exc: self.report({'ERROR'},str(exc)); return {'CANCELLED'}


class CMAI_OT_reference_walk_step(bpy.types.Operator):
    bl_idname='cmai.reference_walk_step'; bl_label='Reference Walk Builder Stage'
    bl_description='Creates unique outputs; stage PASS means executed numerical checks, not visual approval'
    stage: EnumProperty(items=[(key,label,label) for key,label in STAGES])

    def execute(self,context):
        scene=context.scene; state=read_state(scene); stage=self.stage
        try:
            if bpy.app.version<(4,4,0): raise ValueError('Reference Walk Builder requires Blender 4.4+ Action slots; existing legacy buttons remain available.')
            if stage in PENDING: raise ValueError(PENDING[stage])
            # A retry or a failed rebuild must not retain an older downstream PASS.
            invalidates={'walk':['validation','render','export'],
                         'validation':['render','export'],'render':['export']}
            for key in invalidates.get(stage,[]):
                state.setdefault('stages',{})[key]='NOT TESTED'
            if stage=='rig':
                p=scene.cmai_walk; arm,mesh=service.bind_creature(scene,p.rig or context.active_object)
                profile=service.resolve_profile(arm,bpy.path.abspath(p.profile_path) if p.profile_path else None)
                old_frame=scene.frame_current
                try:
                    scene.frame_set(1); anatomy=service.capture_anatomy(arm,mesh,profile)
                finally: scene.frame_set(old_frame)
                out=Path(bpy.path.abspath(p.output))/(time.strftime('walk_%Y%m%d_%H%M%S_')+uuid.uuid4().hex[:8]); out.mkdir(parents=True)
                service.write_json(out/'rig_anatomy.json',anatomy); service.write_json(out/'rig_profile.json',profile)
                state={'run':str(out),'source_scene':scene.name,'source_armature':arm.name,'anatomy':str(out/'rig_anatomy.json'),
                       'profile':profile,'stages':{key:'NOT TESTED' for key,_ in STAGES}}
                state['message']=f'{len(profile["chains"])} connected weighted chains found. Anatomical video identities remain unverified.'
                p.solver_status = 'Existing solver (Pinocchio fallback: no validated per-leg Blender conversion profile)'
            else:
                require(state,'rig'); anatomy=json.loads(Path(state['anatomy']).read_text()); settings=configuration(scene,state['profile'])
                if stage=='standing':
                    source=bpy.data.scenes.get(state['source_scene'])
                    if source is None: raise ValueError('Original source scene is unavailable; reanalyze the standing baseline.')
                    original_settings={k:getattr(scene.cmai_walk,k) for k in ['profile_path','output','external_python','body_height','inward','stride','lift_fraction','cycle_frames','body_bob','phase_json','solver_backend']}
                    context.window.scene=source
                    bpy.ops.scene.new(type='FULL_COPY'); scene=context.window.scene; scene.name='CMAI_Walk_Working_'+uuid.uuid4().hex[:6]
                    for key,value in original_settings.items(): setattr(scene.cmai_walk,key,value)
                    arm,mesh=service.bind_creature(scene)
                    state.update(working_scene=scene.name,working_armature=arm.name,working_mesh=mesh.name)
                    scene.frame_set(1); service.isolate_evaluated_pose(arm)
                    # Restore captured evaluated baseline, never force identity channels.
                    from mathutils import Matrix
                    for p in sorted(arm.pose.bones,key=lambda p:len(p.parent_recursive)):
                        p.matrix=Matrix(anatomy['baseline'][p.name]); bpy.context.view_layer.update()
                    out=new_output(state,'standing')
                    report=service.fit_standing(scene,arm,mesh,anatomy,settings,out)
                    camera=service.setup_preview_camera(scene,mesh,settings['forward_world'],report['ground'])
                    service.write_json(out/'camera_setup.json',camera)
                    state.update(standing_report=str(out/'standing_validation.json'),standing_action=report['action'],standing_dir=str(out))
                    for key in ['standing_preview','waypoints','walk','validation','render','export']: state['stages'][key]='NOT TESTED'
                    state['message']='Standing contacts passed; original scene preserved. Automatic framing is approximate, not calibrated.'
                else:
                    require(state,'standing'); arm,mesh=working_objects(scene,state)
                    standing=json.loads(Path(state['standing_report']).read_text()); out=new_output(state,stage)
                    if stage=='standing_preview':
                        old_action=arm.animation_data.action; old_slot=arm.animation_data.action_slot; old_frame=scene.frame_current
                        try:
                            use_standing_action(scene,arm,state); scene.render.image_settings.file_format='PNG'; scene.render.filepath=str(out/'standing.png')
                            bpy.ops.render.render(write_still=True)
                        finally:
                            arm.animation_data.action=old_action
                            if old_slot: arm.animation_data.action_slot=old_slot
                            scene.frame_set(old_frame)
                        state['standing_preview']=str(out/'standing.png'); state['message']='Standing preview rendered. Visual approval has not been inferred.'
                    elif stage=='waypoints':
                        use_standing_action(scene,arm,state)
                        result=service.generate_waypoints_or_walk(scene,arm,mesh,anatomy,standing,settings,out,plan_only=True)
                        state['waypoints']=str(out/'waypoints.json'); state['message']='Reachable per-leg waypoint poses saved; standing Action restored.'
                        for key in ['walk','validation','render','export']: state['stages'][key]='NOT TESTED'
                    elif stage=='walk':
                        require(state,'waypoints'); use_standing_action(scene,arm,state)
                        for obj in [scene.camera]+[o for o in scene.objects if o.type=='LIGHT' and not o.hide_render]:
                            if obj.animation_data: obj.animation_data_clear()
                        prepared=json.loads(Path(state['waypoints']).read_text())
                        result=service.generate_waypoints_or_walk(scene,arm,mesh,anatomy,standing,settings,out,prepared=prepared)
                        state.update(walk_dir=str(out),walk_action=result['action'],walk_report=str(out/'walk_validation.json'),settings=settings)
                        service.write_json(out/'settings.json',settings)
                        if not all(v['numerical_status']=='PASS' for v in result['legs'].values()): raise ValueError(f'Intermediate leg checks failed. Inspect {out}/walk_validation.json')
                        state['message']='Shared walking Action built. Run Validate Animation before rendering.'
                    elif stage=='validation':
                        require(state,'walk')
                        if not arm.animation_data.action or arm.animation_data.action.name!=state['walk_action']:
                            raise ValueError('The builder walking Action is not active. Select it before validation, or rebuild the walk.')
                        result=service.validate_animation(scene,arm,mesh,anatomy,state['settings'],standing['ground'],out)
                        state['validation_report']=str(out/'animation_validation.json')
                        if result['status']!='PASS': raise ValueError(f'Animation validation failed. Inspect {state["validation_report"]}')
                        state['message']='120-frame numerical/playback checks passed; full mesh collision and visual gait approval remain unverified.'
                    elif stage=='render':
                        require(state,'validation'); require(state,'walk')
                        validation=json.loads(Path(state['validation_report']).read_text())
                        if validation.get('motion_signature')!=service.motion_signature(scene,arm):
                            state['stages']['validation']='NOT TESTED'
                            raise ValueError('Animation or camera changed after validation. Run Validate Animation again.')
                        if service.fingerprint(arm,mesh)!=anatomy['geometry_sha256']:
                            state['stages']['validation']='NOT TESTED'
                            raise ValueError('Rig geometry or mesh weights changed. Reanalyze the original baseline.')
                        py=Path(bpy.path.abspath(scene.cmai_walk.external_python))
                        if not py.is_file(): raise ValueError('Select the existing external Python with OpenCV and imageio-ffmpeg. No packages are installed into Blender.')
                        subprocess.run([str(py),'-c','import cv2, imageio_ffmpeg'],check=True,capture_output=True,timeout=30)
                        (out/'frames').mkdir(); scene.frame_start=1; scene.frame_end=120; scene.render.fps=24
                        scene.render.image_settings.file_format='PNG'; scene.render.filepath=str(out/'frames/walk_')
                        bpy.ops.render.render(animation=True)
                        worker=Path(__file__).with_name('walk_preview_worker.py')
                        process=subprocess.run([str(py),str(worker),str(out)],capture_output=True,text=True,timeout=180)
                        (out/'encoder.log').write_text(process.stdout+'\n'+process.stderr)
                        if process.returncode: raise ValueError(f'Preview encoding/visible-change check failed: {out}/encoder.log')
                        state.update(preview_video=str(out/'walk_5sec.mp4'),preview_report=str(out/'preview_validation.json'))
                        state['message']='120-frame MP4 encoded and decoded; motion checked in every second. Visual gait review is still required.'
            state.setdefault('stages',{})[stage]='PASS'
            if stage in ['standing','walk','validation','render']:
                blend=out/(stage+'.blend'); state[stage+'_blend']=str(blend)
                save_state(scene,state)
                bpy.ops.wm.save_as_mainfile(filepath=str(blend),copy=True)
            else:
                save_state(scene,state)
            self.report({'INFO'},state.get('message','Stage completed'))
            return {'FINISHED'}
        except Exception as exc:
            scene=bpy.context.scene; state.setdefault('stages',{})[stage]='FAIL'; state['message']=str(exc)
            save_state(scene,state); self.report({'ERROR'},str(exc))
            return {'CANCELLED'}


class CMAI_OT_make_seamless_loop(bpy.types.Operator):
    bl_idname='cmai.make_seamless_loop'; bl_label='Make Seamless Loop'
    bl_description='Duplicate the active Action, close its pose endpoint, and save a reusable loop profile'
    def execute(self, context):
        p=context.scene.cmai_walk
        try:
            arm=p.rig or context.active_object
            if arm is None or arm.type!='ARMATURE': raise ValueError('Select an armature with the validated walking Action.')
            result, blend, report, profile = loop_service.create_loop(context.scene, arm, p.loop_output, p.loop_mode)
            validator = Path(__file__).parent.parent / 'tools' / 'validate_eight_leg_walk.py'
            if validator.is_file() and Path(bpy.app.binary_path).is_file():
                validation = report.with_name('mechanical_validation.json')
                proc = subprocess.run([bpy.app.binary_path, '-b', '--python', str(validator), '--',
                                       '--blend', str(blend), '--report', str(validation)],
                                      capture_output=True, text=True, timeout=300)
                mechanical = json.loads(validation.read_text()) if validation.is_file() else {}
                result['mechanical_validation'] = mechanical.get('status', 'FAIL') if proc.returncode == 0 else 'FAIL'
                result['mechanical_validation_report'] = str(validation)
                report.write_text(json.dumps(result, indent=2), encoding='utf-8')
                if proc.returncode != 0 or result['mechanical_validation'] == 'FAIL':
                    raise ValueError(f'Mechanical validation failed; inspect {validation}')
            p.loop_status=result['status']; p.loop_report=str(report)
            self.report({'INFO'}, f"Created {result['duplicate_action']}; endpoint mesh error {result['endpoint_mesh_error']:.3g} BU")
            return {'FINISHED'} if result['status']=='PASS' else {'CANCELLED'}
        except Exception as exc:
            p.loop_status='FAIL'; self.report({'ERROR'},str(exc)); return {'CANCELLED'}


class CMAI_OT_compare_improve_animation(bpy.types.Operator):
    bl_idname='cmai.compare_improve_animation'; bl_label='Compare & Improve Animation'
    bl_description='Run a non-destructive before/after comparison against the earlier Balisk baseline'
    def execute(self, context):
        root=Path(r'C:\Users\rober\CreatureMotionAI')
        report=root/'data/generated/bending_history_comparison.json'
        video=root/'data/generated/bending_history_side_by_side.mp4'
        try:
            script=root/'tools'/'side_by_side_history_video.py'
            py=Path(context.scene.cmai_walk.external_python) if context.scene.cmai_walk.external_python else Path(r'C:\Users\rober\CreatureMotionAI\.venv-dlc\Scripts\python.exe')
            if not py.is_file(): raise ValueError('External Python is not configured; select the project Python with OpenCV.')
            proc=subprocess.run([str(py),str(script)],capture_output=True,text=True,timeout=120)
            if proc.returncode: raise ValueError(proc.stderr or proc.stdout)
            if not report.is_file() or not video.is_file(): raise ValueError('Comparison artifacts were not created.')
            p=context.scene.cmai_walk; p.compare_report=str(report); p.compare_video=str(video)
            self.report({'INFO'},'Comparison complete. No Action was modified; visual approval is required before improvement.')
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'},str(exc)); return {'CANCELLED'}


class CMAI_OT_refit_standing_cameras(bpy.types.Operator):
    bl_idname='cmai.refit_standing_cameras'; bl_label='Match Cameras to Standing Model'
    bl_description='Render both viewing directions and fit independent reference framing; save a new camera copy'
    def execute(self,context):
        from .camera_refit_service import run_calibration
        p=context.scene.cmai_walk; root=Path(bpy.path.abspath(p.project_folder))
        try:
            path=run_calibration(root,bpy.app.binary_path,bpy.path.abspath(p.external_python),bpy.path.abspath(p.standing_model),bpy.path.abspath(p.side_video),bpy.path.abspath(p.front_video) if p.front_video else '',bpy.path.abspath(p.output),bpy.path.abspath(p.best_animation) if p.best_animation else '')
            p.shared_manifest=str(path); m=json.loads(path.read_text()); p.camera_profile=m['camera_profiles']; p.dual_camera_report=m['camera_report']; p.camera_search_status='APPROXIMATE: review upper-body overlays'
            state=read_state(context.scene); state['shared_manifest']=str(path); save_state(context.scene,state)
            self.report({'INFO'},'Camera fit rendered and saved; original scene and Actions unchanged.')
            return {'FINISHED'}
        except Exception as exc:
            p.camera_search_status='FAIL'; self.report({'ERROR'},str(exc)); return {'CANCELLED'}


class CMAI_OT_test_camera_pose(bpy.types.Operator):
    bl_idname='cmai.test_camera_pose'; bl_label='Test Camera-Constrained Pose'
    bl_description='Render small existing-IK pose hypotheses in the calibrated copy; no walking Action changes'
    def execute(self,context):
        from .camera_refit_service import test_pose
        p=context.scene.cmai_walk
        try:
            report=test_pose(Path(bpy.path.abspath(p.project_folder)),bpy.app.binary_path,bpy.path.abspath(p.external_python),bpy.path.abspath(p.shared_manifest))
            p.compare_report=report; self.report({'INFO'},'Pose hypotheses rendered; acceptance remains unverified. See report.')
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'},str(exc)); return {'CANCELLED'}


class CMAI_OT_measure_side_video(bpy.types.Operator):
    bl_idname='cmai.measure_side_video'; bl_label='Measure Side Video'
    bl_description='Save timestamped image measurements and conservative gait evidence in the shared workflow'
    def execute(self,context):
        from .camera_refit_service import measure_video
        p=context.scene.cmai_walk
        try:
            path=measure_video(bpy.path.abspath(p.project_folder),bpy.path.abspath(p.external_python),bpy.path.abspath(p.shared_manifest))
            p.shared_manifest=str(path)
            manifest=json.loads(path.read_text()); timing=json.loads(Path(manifest['gait_timing']).read_text())
            p.reference_pose_status='Measurements saved; timing '+timing['status']
            state=read_state(context.scene); state['shared_manifest']=str(path); save_state(context.scene,state)
            self.report({'INFO'},p.reference_pose_status); return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'},str(exc)); return {'CANCELLED'}


class CMAI_OT_improve_reference_pose(bpy.types.Operator):
    bl_idname='cmai.improve_reference_pose'; bl_label='Improve Pose From Reference'
    bl_description='Compare bounded existing-solver pose candidates with the preserved walk; do not replace its Action'
    def execute(self,context):
        from .camera_refit_service import improve_pose
        p=context.scene.cmai_walk
        try:
            path=improve_pose(bpy.path.abspath(p.project_folder),bpy.app.binary_path,bpy.path.abspath(p.external_python),bpy.path.abspath(p.shared_manifest),bpy.path.abspath(p.profile_path) if p.profile_path else '',0 if p.auto_reference_pose else p.pose_reference_frame)
            p.shared_manifest=str(path); manifest=json.loads(path.read_text())
            p.compare_report=manifest['pose_report']; p.reference_pose_status=manifest['pose_reconstruction']
            state=read_state(context.scene); state['shared_manifest']=str(path); save_state(context.scene,state)
            self.report({'INFO'},p.reference_pose_status+'; original walk preserved.'); return {'FINISHED'}
        except Exception as exc:
            p.reference_pose_status='FAIL'; self.report({'ERROR'},str(exc)); return {'CANCELLED'}

class CMAI_OT_compare_image_landmarks(bpy.types.Operator):
    bl_idname='cmai.compare_image_landmarks'; bl_label='Compare Image Landmarks'
    def execute(self,context):
        from .camera_refit_service import compare_image_landmarks
        p=context.scene.cmai_walk
        try:
            path=compare_image_landmarks(bpy.path.abspath(p.project_folder),bpy.app.binary_path,bpy.path.abspath(p.shared_manifest),36,bpy.path.abspath(p.external_python))
            p.shared_manifest=str(path); p.compare_report=str(path.parent/'image_landmark_report.json')
            p.reference_pose_status='IMAGE_LANDMARKS_REVIEWED'
            self.report({'INFO'},'Image landmark comparison saved; verified correspondences remain required.')
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'},str(exc)); return {'CANCELLED'}


class CMAI_PT_reference_walk(bpy.types.Panel):
    bl_label='Reference Walk Builder'; bl_idname='CMAI_PT_reference_walk'
    bl_space_type='VIEW_3D'; bl_region_type='UI'; bl_category='Creature Motion AI'; bl_order=-10
    def draw(self,context):
        layout=self.layout; p=context.scene.cmai_walk; state=read_state(context.scene)
        layout.label(text='Review workflow — PASS is not visual approval',icon='INFO')
        if hasattr(context.scene,'cmai_video'): layout.prop(context.scene,'cmai_video',text='Reference MP4')
        layout.prop(p,'rig'); layout.prop(p,'profile_path'); layout.operator('cmai.walk_load_balisk_profile')
        layout.prop(p,'output'); layout.prop(p,'external_python')
        workflow=layout.box(); workflow.label(text='Complete Animation Workflow', icon='SEQUENCE')
        workflow.label(text='Load Reference Videos', icon='FILE_FOLDER')
        workflow.prop(p,'side_video',text='Side Reference Video'); workflow.prop(p,'front_video',text='Front Reference Video (optional)')
        workflow.operator('cmai.analyze_video_and_rig', text='Analyze Video and Rig', icon='VIEWZOOM')
        workflow.operator('cmai.review_all_landmarks', text='Review Leg Identities', icon='IMAGE_DATA')
        workflow.label(text='Motion Solver: '+p.solver_backend+' / '+p.solver_status, icon='POSE_HLT')
        workflow.label(text='Pinocchio remains gated until moving Blender conversion passes.', icon='INFO')
        row=workflow.row(align=True); row.operator('cmai.reference_walk_step', text='Generate Walk Animation', icon='ANIM').stage='walk'; row.operator('cmai.compare_improve_animation', text='Compare With Reference', icon='VIEWZOOM')
        workflow.label(text='Improve Animation requires visual approval; original Actions are preserved.', icon='INFO')
        auto=layout.box(); auto.label(text='Universal Creature Detection')
        auto.operator('cmai.detect_creature_automatically')
        auto.label(text=p.auto_status,icon='INFO')
        auto.prop(p,'auto_report')
        auto.operator('cmai.generate_auto_walk_preview')
        analysis=layout.box(); analysis.label(text='Video + Rig Combined Analysis',icon='VIEWZOOM')
        analysis.prop(p,'analysis_video'); analysis.operator('cmai.analyze_video_and_rig')
        analysis.label(text=p.analysis_status,icon='INFO')
        if p.analysis_report: analysis.prop(p,'analysis_report')
        dual=layout.box(); dual.label(text='Independent Reference Cameras',icon='CAMERA_DATA')
        dual.label(text='Side drives gait; Front is optional secondary guidance.',icon='INFO')
        dual.operator('cmai.analyze_reference_camera')
        dual.prop(p,'side_video',text='Side Reference Video'); dual.prop(p,'front_video',text='Front Reference Video')
        dual.operator('cmai.estimate_dual_reference_cameras')
        dual.prop(p,'project_folder'); dual.prop(p,'standing_model'); dual.prop(p,'best_animation')
        dual.operator('cmai.refit_standing_cameras')
        dual.operator('cmai.test_camera_pose')
        dual.label(text=p.camera_search_status)
        if p.shared_manifest: dual.prop(p,'shared_manifest')
        dual.operator('cmai.measure_side_video')
        dual.prop(p,'auto_reference_pose')
        if not p.auto_reference_pose: dual.prop(p,'pose_reference_frame')
        dual.operator('cmai.improve_reference_pose')
        dual.operator('cmai.compare_image_landmarks')
        dual.label(text=p.reference_pose_status)
        if p.dual_camera_report: dual.prop(p,'dual_camera_report')
        box=layout.box()
        box.prop(p,'solver_backend'); box.label(text=f'Solver status: {p.solver_status}', icon='INFO')
        for name in ['body_height','inward','stride','lift_fraction','cycle_frames','body_bob','phase_json']: box.prop(p,name)
        for key,label in STAGES:
            row=layout.row(align=True); button=row.row(align=True); button.enabled=key not in PENDING
            button.operator('cmai.reference_walk_step',text=label).stage=key
            status=state.get('stages',{}).get(key,'NOT TESTED')
            row.label(text=status,icon={'PASS':'CHECKMARK','FAIL':'ERROR','NOT TESTED':'QUESTION'}[status])
        loop=layout.box(); loop.label(text='Seamless Loop', icon='LOOP_BACK')
        loop.prop(p,'loop_mode'); loop.prop(p,'loop_output'); loop.operator('cmai.make_seamless_loop')
        loop.label(text=f'Loop status: {p.loop_status}', icon='CHECKMARK' if p.loop_status=='PASS' else 'QUESTION')
        if p.loop_report: loop.prop(p,'loop_report')
        compare=layout.box(); compare.label(text='Reference Comparison / Improvement', icon='VIEWZOOM')
        compare.operator('cmai.compare_improve_animation')
        if p.compare_report: compare.prop(p,'compare_report')
        if p.compare_video: compare.prop(p,'compare_video')
        layout.label(text='Video analysis, calibrated camera and FBX: pending')
        if state.get('message'):
            import textwrap
            for line in textwrap.wrap(state['message'],48): layout.label(text=line)
        if state.get('preview_video'): layout.label(text='Preview saved in the current output run',icon='FILE_MOVIE')


CLASSES=(CMAI_WalkSettings,CMAI_OT_walk_preset,CMAI_OT_detect_creature,CMAI_OT_generate_auto_preview,CMAI_OT_analyze_video_rig,CMAI_OT_estimate_dual_cameras,CMAI_OT_analyze_reference_camera,CMAI_OT_make_seamless_loop,CMAI_OT_compare_improve_animation,CMAI_OT_reference_walk_step,CMAI_OT_refit_standing_cameras,CMAI_OT_test_camera_pose,CMAI_OT_measure_side_video,CMAI_OT_improve_reference_pose,CMAI_OT_compare_image_landmarks,CMAI_PT_reference_walk)
def register():
    for cls in CLASSES: bpy.utils.register_class(cls)
    bpy.types.Scene.cmai_walk=PointerProperty(type=CMAI_WalkSettings)
def unregister():
    del bpy.types.Scene.cmai_walk
    for cls in reversed(CLASSES): bpy.utils.unregister_class(cls)
