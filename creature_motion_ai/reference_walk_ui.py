"""Guided sidebar for the executed standing-fit/waypoint workflow."""
import json
import subprocess
import time
import uuid
from pathlib import Path

import bpy
from bpy.props import StringProperty, FloatProperty, IntProperty, PointerProperty, EnumProperty
from . import reference_walk as service

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


def configuration(scene,profile):
    p=scene.cmai_walk
    config={**profile,'cycle_frames':int(p.cycle_frames),'body_height':p.body_height,'inward':p.inward,
        'shared_stride':p.stride,'lift_fraction':p.lift_fraction,'body_bob':p.body_bob,
        'world_planted_support':True,'contact_xy_tolerance':.0008,'fps':24,
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
            else:
                require(state,'rig'); anatomy=json.loads(Path(state['anatomy']).read_text()); settings=configuration(scene,state['profile'])
                if stage=='standing':
                    source=bpy.data.scenes.get(state['source_scene'])
                    if source is None: raise ValueError('Original source scene is unavailable; reanalyze the standing baseline.')
                    original_settings={k:getattr(scene.cmai_walk,k) for k in ['profile_path','output','external_python','body_height','inward','stride','lift_fraction','cycle_frames','body_bob','phase_json']}
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


class CMAI_PT_reference_walk(bpy.types.Panel):
    bl_label='Reference Walk Builder'; bl_idname='CMAI_PT_reference_walk'
    bl_space_type='VIEW_3D'; bl_region_type='UI'; bl_category='Creature Motion AI'; bl_order=-10
    def draw(self,context):
        layout=self.layout; p=context.scene.cmai_walk; state=read_state(context.scene)
        layout.label(text='Review workflow — PASS is not visual approval',icon='INFO')
        if hasattr(context.scene,'cmai_video'): layout.prop(context.scene,'cmai_video',text='Reference MP4')
        layout.prop(p,'rig'); layout.prop(p,'profile_path'); layout.operator('cmai.walk_load_balisk_profile')
        layout.prop(p,'output'); layout.prop(p,'external_python')
        box=layout.box()
        for name in ['body_height','inward','stride','lift_fraction','cycle_frames','body_bob','phase_json']: box.prop(p,name)
        for key,label in STAGES:
            row=layout.row(align=True); button=row.row(align=True); button.enabled=key not in PENDING
            button.operator('cmai.reference_walk_step',text=label).stage=key
            status=state.get('stages',{}).get(key,'NOT TESTED')
            row.label(text=status,icon={'PASS':'CHECKMARK','FAIL':'ERROR','NOT TESTED':'QUESTION'}[status])
        layout.label(text='Video analysis, calibrated camera and FBX: pending')
        if state.get('message'):
            import textwrap
            for line in textwrap.wrap(state['message'],48): layout.label(text=line)
        if state.get('preview_video'): layout.label(text='Preview saved in the current output run',icon='FILE_MOVIE')


CLASSES=(CMAI_WalkSettings,CMAI_OT_walk_preset,CMAI_OT_reference_walk_step,CMAI_PT_reference_walk)
def register():
    for cls in CLASSES: bpy.utils.register_class(cls)
    bpy.types.Scene.cmai_walk=PointerProperty(type=CMAI_WalkSettings)
def unregister():
    del bpy.types.Scene.cmai_walk
    for cls in reversed(CLASSES): bpy.utils.unregister_class(cls)
