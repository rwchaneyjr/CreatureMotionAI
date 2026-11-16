"""Geometry-first anatomy proposals for unfamiliar creature armatures.

This module proposes leg chains; it never silently assigns uncertain anatomy to
an animation. Names are used only as weak evidence after hierarchy and shape.
"""
from __future__ import annotations

from mathutils import Vector


def _world_point(arm, bone, point):
    return arm.matrix_world @ point


def _chain_from(bone, max_links=4):
    chain = [bone]
    current = bone
    while len(chain) < max_links:
        children = [child for child in current.children if child.use_deform]
        if len(children) != 1:
            break
        current = children[0]
        chain.append(current)
    return chain


def _name_hint(names):
    text = ' '.join(names).lower()
    score = 0.0
    if any(x in text for x in ('leg', 'limb', 'foot', 'paw', 'tentacle')):
        score += .12
    if 'arm' in text or 'hand' in text:
        score -= .16
    if any(x in text for x in ('spine', 'body', 'tail', 'head', 'neck', 'wing')):
        score -= .18
    return score


def _candidate_score(arm, chain, center, up=Vector((0, 0, 1))):
    if len(chain) < 3:
        return None
    axial_tokens=('tail','spine','body','torso','neck','head','wing')
    if any(token in ' '.join(b.name for b in chain).lower() for token in axial_tokens):
        return None
    points = [_world_point(arm, chain[0], chain[0].head)]
    points.extend(_world_point(arm, bone, bone.tail) for bone in chain[:3])
    vectors = [points[i + 1] - points[i] for i in range(3)]
    lengths = [v.length for v in vectors]
    if min(lengths) < 1e-6:
        return None
    outward = (points[0] - center).normalized()
    terminal = vectors[-1].normalized()
    whole = (points[-1] - points[0]).normalized()
    # Legs normally extend away from the body and finish downwards.
    outward_score = max(0.0, min(1.0, outward.dot((points[-1] - center).normalized())))
    # The terminal bone may be a level foot segment. Use the full chain's
    # hip-to-foot trajectory as the primary vertical evidence, with the last
    # segment only as a weak supporting signal.
    down_score = max(0.0, min(1.0, -.5 * whole.dot(up) - .15 * terminal.dot(up) + .5))
    end_height_score = max(0.0, min(1.0, (center.z - points[-1].z) / max(.001, (center.z - min(p.z for p in points)))))
    bend = vectors[0].cross(vectors[1]).length / (lengths[0] * lengths[1])
    bend_score = max(0.0, min(1.0, bend * 2.0))
    score = .32 * outward_score + .26 * down_score + .18 * end_height_score + .22 * bend_score
    score += _name_hint([b.name for b in chain])
    score = max(0.0, min(1.0, score))
    return {
        'bones': [b.name for b in chain[:3]],
        'all_connected_bones': [b.name for b in chain],
        'score': score,
        'confidence': 'HIGH' if score >= .72 else 'MEDIUM' if score >= .52 else 'LOW',
        'evidence': {
            'outward': outward_score,
            'downward_terminal': down_score,
            'end_height': end_height_score,
            'joint_bend': bend_score,
            'name_hint': _name_hint([b.name for b in chain]),
        },
        'lengths': lengths,
        'points': [list(p) for p in points],
        'confirmed': False,
    }


def detect_anatomy(arm):
    """Return read-only leg candidates and confidence without changing Blender."""
    deform = [b for b in arm.data.bones if b.use_deform]
    if not deform:
        raise ValueError('No deform bones were found on the selected armature.')
    points = [_world_point(arm, b, b.head_local) for b in deform]
    center = sum(points, Vector()) / len(points)
    candidates = []
    for bone in deform:
        # Start at branch points or top-level limb candidates. This avoids
        # returning every sliding window through the same chain.
        if bone.parent and len([c for c in bone.parent.children if c.use_deform]) == 1:
            continue
        item = _candidate_score(arm, _chain_from(bone), center)
        if item:
            item['root'] = bone.name
            candidates.append(item)
    candidates.sort(key=lambda item: item['score'], reverse=True)
    # In humanoid rigs, arms can have the same three-link shape as legs.
    # When explicit leg/foot candidates exist, keep arm candidates as
    # alternatives for review instead of treating them as walking limbs.
    named_leg_candidates=[x for x in candidates if any(t in ' '.join(x['bones']).lower() for t in ('leg','foot','paw'))]
    named_arm_candidates=[x for x in candidates if 'arm' in ' '.join(x['bones']).lower()]
    # Arms are excluded only when a paired leg set already explains the
    # expected limb count. In creatures that call front legs "Arm", retain
    # them as candidates and lower confidence for review.
    if len(named_leg_candidates) >= 2 and len(named_arm_candidates) <= len(named_leg_candidates):
        for item in candidates:
            if 'arm' in ' '.join(item['bones']).lower() or 'hand' in ' '.join(item['bones']).lower():
                item['excluded_reason']='arm-like candidate; retained as alternative, not selected'
    # Select non-overlapping proposals greedily; keep alternatives in report.
    selected = []
    used = set()
    for item in candidates:
        if item.get('excluded_reason'):
            continue
        overlap = used.intersection(item['bones'])
        if overlap:
            continue
        selected.append(item)
        used.update(item['bones'])
    # A count alone is never treated as proof. Confidence is reduced when the
    # detector sees a partial or ambiguous set of chains.
    count = len(selected)
    expected = count in (2, 4, 6, 8) and count > 0
    arm_selected = sum('arm' in ' '.join(x['bones']).lower() for x in selected)
    report = {
        'schema_version': 1,
        'armature': arm.name,
        'bone_count': len(arm.data.bones),
        'deform_bone_count': len(deform),
        'candidate_count': len(candidates),
        'selected_leg_count': count,
        'selected_chains': selected,
        'alternatives': candidates,
        'status': 'PROPOSAL_REQUIRES_REVIEW',
        'mapping_confidence': 'HIGH' if expected and arm_selected == 0 and all(x['confidence'] == 'HIGH' for x in selected) else 'MEDIUM' if selected else 'LOW',
        'arm_like_selected_count': arm_selected,
        'confirmed': False,
        'warnings': [
            'Bone names are weak evidence only; review the highlighted chains before animation.',
            'Hidden limbs, disconnected chains, non-leg appendages, and unusual rigs may be misclassified.',
        ],
    }
    return report


def profile_from_detection(report, root_bone):
    """Build an unconfirmed profile suitable for review, never auto-approved."""
    chains = {}
    offsets = {}
    for index, item in enumerate(report['selected_chains']):
        label = f'auto_leg_{index + 1:02d}'
        chains[label] = item['bones']
        offsets[label] = index / max(1, len(report['selected_chains']))
    return {
        'name': f'auto_profile_{report["armature"]}',
        'chains': chains,
        'root_bone': root_bone,
        'phase_offsets': offsets,
        'mapping_status': 'AUTO_PROPOSAL_UNCONFIRMED',
        'detector_confidence': report['mapping_confidence'],
        'confirmed': False,
    }
