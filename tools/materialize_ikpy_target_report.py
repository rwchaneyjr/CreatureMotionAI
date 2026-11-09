import json, sys
from pathlib import Path

src, name, dst = sys.argv[1:4]
d = json.loads(Path(src).read_text())
if name in ('step', 'step_support', 'step_visible', 'orientation_step'):
    wanted = {x['name']: x for x in d['tests']}
    if name == 'orientation_step':
        wanted = next(x for x in d['tests'] if x['name'] == 'forward_up')
        d['step_joint_matrices'] = [d['neutral_joint_matrices'], d['neutral_joint_matrices'], wanted['joint_matrices'], d['neutral_joint_matrices'], d['neutral_joint_matrices']]
        d['step_pose_frames'] = [1, 6, 12, 18, 25]
        d['step_mode'] = 'orientation_step'
        d['orientation_constrained'] = True
    elif name == 'step_visible':
        d['step_joint_matrices'] = [d['neutral_joint_matrices'], wanted['lift']['joint_matrices'], wanted['forward_up']['joint_matrices'], wanted['forward_down']['joint_matrices'], d['neutral_joint_matrices']]
        # Put the clearly lifted pose on frame 12 for the visual gate; the
        # smaller forward-up pose follows so the foot remains easy to inspect.
        d['step_pose_frames'] = [1, 4, 12, 16, 20, 22, 25]
    elif name == 'step_support':
        # Rest/support, swing lift, forward/up, plant/support, return.
        d['step_joint_matrices'] = [d['neutral_joint_matrices'], wanted['lift']['joint_matrices'], wanted['forward_up']['joint_matrices'], wanted['forward_down']['joint_matrices'], d['neutral_joint_matrices']]
        d['step_pose_frames'] = [1, 21, 45, 75, 120]
    else:
        d['step_joint_matrices'] = [d['neutral_joint_matrices'], wanted['lift']['joint_matrices'], wanted['forward_up']['joint_matrices'], wanted['forward_down']['joint_matrices'], d['neutral_joint_matrices']]
    Path(dst).write_text(json.dumps(d, indent=2), encoding='utf-8')
    raise SystemExit
t = next(x for x in d['tests'] if x['name'] == name)
out = dict(d)
out['target'] = t['target']
out['moved_solution'] = t['solution']
out['moved_joint_matrices'] = t['joint_matrices']
out['moved_fk_endpoint'] = t['fk_endpoint']
out['moved_error'] = t['error']
Path(dst).write_text(json.dumps(out, indent=2), encoding='utf-8')
