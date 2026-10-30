"""Creature-independent armature inspection and profile generation."""
import json
from pathlib import Path


def _category(name):
    value = name.lower()
    if any(token in value for token in ("tail", "spine", "body", "torso")):
        return "axial"
    if any(token in value for token in ("head", "neck", "skull")):
        return "head_neck"
    if any(token in value for token in ("wing", "feather")):
        return "wing"
    if any(token in value for token in ("leg", "arm", "limb", "tentacle", "pincer")):
        return "limb"
    return "other"


def _role_hint(name):
    value = name.lower()
    side = "left" if any(token in value for token in (".l", "_l", "left")) else "right" if any(token in value for token in (".r", "_r", "right")) else None
    if "tail" in value:
        role = "tail"
    elif any(token in value for token in ("head", "neck")):
        role = "head_neck"
    elif any(token in value for token in ("wing", "feather")):
        role = "wing"
    elif any(token in value for token in ("leg", "arm", "limb", "tentacle", "pincer")):
        role = "limb"
    elif any(token in value for token in ("spine", "body", "torso")):
        role = "body"
    else:
        role = "unclassified"
    return {"role": role, "side": side}


def _chains(armature):
    chains = []
    for bone in armature.data.bones:
        if bone.parent and len(bone.parent.children) == 1:
            continue
        for child in bone.children:
            chain = [bone.name]
            current = child
            while current:
                chain.append(current.name)
                if len(current.children) != 1:
                    break
                current = current.children[0]
            chains.append({"root": bone.name, "bones": chain, "category": _category(bone.name)})
    return chains


def inspect_armature(armature):
    bones = []
    for bone in armature.data.bones:
        bones.append({
            "name": bone.name,
            "parent": bone.parent.name if bone.parent else None,
            "children": [child.name for child in bone.children],
            "head": list(bone.head_local),
            "tail": list(bone.tail_local),
            "length": bone.length,
            "use_deform": bone.use_deform,
            "category": _category(bone.name),
        })
    return {"armature": armature.name, "bones": bones, "chains": _chains(armature)}


def write_profile(armature, output_path):
    profile = inspect_armature(armature)
    profile["format"] = "creature_motion_ai.skeleton_profile.v1"
    profile["notes"] = "Generated from the armature hierarchy; mapping is intentionally unresolved."
    profile["mapping"] = {
        "landmark_to_chain": {},
        "chain_assignments": [
            {"chain": chain["bones"], "suggestion": _role_hint(chain["root"]), "confirmed": False}
            for chain in profile["chains"]
        ],
        "manual_review_required": True,
        "guidance": "Review chain candidates before solving video motion.",
    }
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    return path
