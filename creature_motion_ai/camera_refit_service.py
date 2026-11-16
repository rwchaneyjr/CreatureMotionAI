"""Shared manifest for the sidebar camera workflow and its background workers."""
import json
import subprocess
import uuid
from pathlib import Path


def _run_worker(command, root, log_path, timeout):
    """Keep the failing worker and its complete output discoverable in Blender."""
    try:
        with log_path.open('w') as log:
            subprocess.run(list(map(str, command)), cwd=root, stdout=log,
                           stderr=subprocess.STDOUT, check=True, timeout=timeout)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f'Camera workflow worker failed. See {log_path}: {exc}') from exc


def run_calibration(root, blender, python, standing, side, front, output, best_animation=''):
    root=Path(root).resolve(); output=Path(output).resolve()
    for value in (standing,side,python):
        if not Path(value).is_file(): raise ValueError(f'File unavailable: {value}')
    if front and not Path(front).is_file(): raise ValueError(f'Front video unavailable: {front}')
    if best_animation and not Path(best_animation).is_file(): raise ValueError(f'Preserved animation unavailable: {best_animation}')
    run=output/('camera_refit_'+uuid.uuid4().hex[:10]); run.mkdir(parents=True)
    request=dict(standing_model=str(standing),side_video=str(side),front_video=str(front),best_animation=str(best_animation),timing_source='side',front_timing_used=False)
    (run/'request.json').write_text(json.dumps(request,indent=2))
    renderer=root/'tools/calibrate_standing_views_blender.py'; scorer=root/'tools/score_standing_camera_refit.py'
    commands=[[blender,'--factory-startup','-b','--python-exit-code','1','--python',str(renderer),'--',str(run),'search'],[python,str(scorer),str(run)],[blender,'--factory-startup','-b','--python-exit-code','1','--python',str(renderer),'--',str(run),'selected'],[python,str(scorer),str(run),'finish']]
    for i,cmd in enumerate(commands):
        _run_worker(cmd, root, run/f'worker_{i}.log', 600)
    report=json.loads((run/'calibration_report.json').read_text())
    manifest=dict(schema_version=1,inputs=request,camera_profiles=str(run/'camera_profiles.json'),camera_report=str(run/'calibration_report.json'),calibrated_model=str(run/'standing_calibrated_cameras.blend'),measured_positions=None,gait_timing=None,best_validated_animation=str(best_animation),pose_reconstruction='NOT TESTED',automatic_improvement='NOT TESTED',camera_status='APPROXIMATE')
    (run/'workflow_manifest.json').write_text(json.dumps(manifest,indent=2))
    return run/'workflow_manifest.json'

def test_pose(root,blender,python,manifest_path):
    root=Path(root).resolve(); path=Path(manifest_path).resolve(); manifest=json.loads(path.read_text()); run=path.parent
    if (run/'pose_trials.json').exists(): raise ValueError('Pose trial already exists for this calibration; preserve it and start a new calibration run.')
    commands=[[blender,'--factory-startup','-b','--python-exit-code','1','--python',str(root/'tools/test_camera_pose_constraints.py'),'--',str(run)],[python,str(root/'tools/score_camera_pose_trials.py'),str(run)]]
    for i,cmd in enumerate(commands):
        _run_worker(cmd, root, run/f'pose_worker_{i}_{uuid.uuid4().hex[:8]}.log', 300)
    manifest['pose_reconstruction']='NOT ACCEPTED'; manifest['pose_report']=str(run/'pose_comparison_report.json')
    path.write_text(json.dumps(manifest,indent=2)); return manifest['pose_report']


def measure_video(root, python, manifest_path):
    root = Path(root).resolve()
    source = Path(manifest_path).resolve()
    manifest = json.loads(source.read_text(encoding='utf-8-sig'))
    run = source.parent / ('evidence_' + uuid.uuid4().hex[:10])
    run.mkdir()
    _run_worker([python, '-m', 'creature_motion_ai.reference_evidence', str(source), str(run)],
                root, run/'measurement.log', 300)
    manifest['parent_manifest'] = str(source)
    manifest['measured_positions'] = str(run/'measured_positions.json')
    manifest['gait_timing'] = str(run/'gait_timing.json')
    manifest['measurement_review'] = str(run/'measurement_review.jpg')
    manifest['automatic_improvement'] = 'NOT TESTED'
    target = run/'workflow_manifest.json'
    target.write_text(json.dumps(manifest, indent=2))
    return target


def improve_pose(root, blender, python, manifest_path, rig_profile, reference_frame=0):
    root = Path(root).resolve()
    source = Path(manifest_path).resolve()
    manifest = json.loads(source.read_text(encoding='utf-8-sig'))
    if not manifest.get('measured_positions'):
        raise ValueError('Run Measure Side Video first. No animation changes made.')
    for key in ('best_validated_animation', 'camera_profiles', 'measured_positions'):
        if not Path(manifest[key]).is_file(): raise ValueError('Missing workflow input: '+key)
    from .reference_evidence import select_reference_pose
    measured=json.loads(Path(manifest['measured_positions']).read_text())
    selection=select_reference_pose(measured,manifest['inputs']['side_video'])
    if reference_frame:
        matching=[r for r in measured['frames'] if r['frame']==reference_frame]
        if not matching or matching[0].get('status')!='MEASURED_IMAGE_ONLY' or matching[0].get('clipped',True):
            raise ValueError('Requested reference frame lacks an intact measured silhouette.')
        selection=dict(frame=reference_frame,mode='EXPLICIT_FRAME',leg_identity='UNVERIFIED')
    reference_frame=selection['frame']
    run = source.parent / ('pose_improvement_' + uuid.uuid4().hex[:10]); run.mkdir()
    request = dict(manifest=manifest, rig_profile=str(rig_profile), reference_frame=reference_frame,
                   reference_selection=selection,python=str(python))
    (run/'request.json').write_text(json.dumps(request, indent=2))
    commands = [
        [blender,'--factory-startup','-b','--python-exit-code','1','--python',str(root/'tools/run_reference_pose_iteration.py'),'--',str(run)],
        [python,'-m','creature_motion_ai.pose_comparison',str(run)],
    ]
    for i, command in enumerate(commands):
        _run_worker(command,root,run/f'worker_{i}.log',600)
    result=json.loads((run/'pose_improvement_report.json').read_text())
    manifest.update(parent_manifest=str(source), pose_report=str(run/'pose_improvement_report.json'),
                    automatic_improvement=result['status'], pose_reconstruction=result['status'])
    manifest['reference_pose_selection']=selection
    if result['status']=='PASS_APPROXIMATE_SINGLE_POSE':
        accepted=next(row for row in result['candidates'] if row['candidate']==result['best_candidate'])
        manifest['accepted_single_pose']=accepted['diagnostic_blend']
    # A pose candidate never replaces the best walking Action.
    target=run/'workflow_manifest.json'; target.write_text(json.dumps(manifest,indent=2))
    return target

def compare_image_landmarks(root, blender, manifest_path, frame=36, python=None):
    root=Path(root).resolve(); source=Path(manifest_path).resolve()
    manifest=json.loads(source.read_text(encoding="utf-8-sig"))
    run=source.parent/("image_landmarks_"+uuid.uuid4().hex[:10]); run.mkdir()
    request={"source":manifest["best_validated_animation"],"video":manifest["inputs"]["side_video"],"camera_profiles":manifest["camera_profiles"],"frame":int(frame),"blender_frame":int(manifest.get("selected_blender_frame",69))}
    (run/"request.json").write_text(json.dumps(request,indent=2))
    _run_worker([blender,"--factory-startup","-b","--python-exit-code","1","--python",str(root/"tools/run_image_landmark_comparison.py"),"--",str(run)],root,run/"worker.log",300)
    if not python: raise ValueError("OpenCV Python environment required")
    _run_worker([python,str(root/"tools/compose_image_landmark_comparison.py"),str(run),"fit"],root,run/"camera_fit.log",120)
    _run_worker([blender,"--factory-startup","-b","--python-exit-code","1","--python",str(root/"tools/run_image_landmark_comparison.py"),"--",str(run)],root,run/"aligned_render.log",300)
    _run_worker([python,str(root/"tools/compose_image_landmark_comparison.py"),str(run),"margin"],root,run/"margin.log",120)
    adjustment=json.loads((run/"camera_adjustment.json").read_text())
    if adjustment.get("actual_render_margin_correction_px"):
        _run_worker([blender,"--factory-startup","-b","--python-exit-code","1","--python",str(root/"tools/run_image_landmark_comparison.py"),"--",str(run)],root,run/"framed_render.log",300)
    _run_worker([python,str(root/"tools/compose_image_landmark_comparison.py"),str(run),"finish"],root,run/"compose.log",120)
    report=json.loads((run/"image_landmark_report.json").read_text())
    manifest.update(image_landmark_report=str(run/"image_landmark_report.json"),image_landmark_comparison=str(run/"image_landmark_comparison.png"))
    target=run/"workflow_manifest.json"; target.write_text(json.dumps(manifest,indent=2)); return target
