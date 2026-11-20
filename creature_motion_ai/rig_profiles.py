"""Reusable creature rig profiles and conservative armature inspection.

Profiles describe anatomy; they do not alter meshes, armatures, or actions.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import re
from typing import Any


@dataclass(frozen=True)
class LegChain:
    name: str
    bones: tuple[str, ...]
    side: str = "center"
    station: int = 0
    contact_bone: str | None = None


@dataclass(frozen=True)
class SkeletonProfile:
    name: str
    legs: tuple[LegChain, ...]
    heads: tuple[str, ...] = ()
    tails: tuple[str, ...] = ()
    wings: tuple[str, ...] = ()
    body: tuple[str, ...] = ()
    confirmed: bool = False
    schema_version: int = 2

    @property
    def leg_count(self) -> int:
        return len(self.legs)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "legs": [asdict(x) for x in self.legs],
            "heads": list(self.heads),
            "tails": list(self.tails),
            "wings": list(self.wings),
            "body": list(self.body),
            "confirmed": self.confirmed,
            "schema_version": self.schema_version,
        }


def profile_from_bones(bone_names: list[str], *, name: str = "auto") -> SkeletonProfile:
    """Propose leg chains from common numbered bone naming conventions.

    This is deliberately a proposal: uncertain mappings must be reviewed
    before animation is allowed to modify an armature.
    """
    prefixes = {}
    for bone in bone_names:
        for suffix in ("_01", "_upper"):
            if bone.endswith(suffix):
                prefixes.setdefault(bone[: -len(suffix)], set()).add(bone)
                break
    legs = []
    for prefix in sorted(prefixes):
        if not prefix.startswith("Leg_"):
            continue
        chain = tuple(
            x for x in (f"{prefix}_01", f"{prefix}_02", f"{prefix}_03") if x in bone_names
        )
        if len(chain) < 2:
            continue
        side = "left" if ".L" in prefix else "right" if ".R" in prefix else "center"
        if "MidFront" in prefix:
            station = 1
        elif "MidRear" in prefix:
            station = 2
        elif "Front" in prefix:
            station = 0
        else:
            station = 3
        legs.append(LegChain(prefix, chain, side, station))
    return SkeletonProfile(name=name, legs=tuple(legs))


def inspect_armature(armature: Any) -> dict[str, Any]:
    """Read-only armature summary for model-independent setup and review."""
    bones = list(armature.data.bones)
    profile = profile_from_bones([b.name for b in bones], name=armature.name)
    return {
        "armature": armature.name,
        "bone_count": len(bones),
        "leg_count_proposed": profile.leg_count,
        "profile": profile.to_dict(),
        "rest_pose_preserved": True,
        "mapping_status": "proposal_requires_review",
    }


def propose_anatomy_profile(armature: Any) -> dict[str, Any]:
    """Propose anatomy from names *and actual parent hierarchy*.

    The result is never treated as approved. Naming is only a candidate signal;
    each limb must be reviewed before downstream fitting/locking can use it.
    Numbered limbs with a common prefix are grouped, then checked for a contiguous
    parent chain. Optional wing, tail, head, and body roles are reported separately.
    """
    bones = armature.data.bones
    names = {b.name for b in bones}
    groups: dict[str, dict[int, str]] = {}
    for name in names:
        match = re.match(r"^(.*?)[._-](\d{1,2})$", name)
        if match:
            prefix, number = match.group(1), int(match.group(2))
            groups.setdefault(prefix, {})[number] = name

    legs = []
    leg_hints = re.compile(r"(^|[._-])(leg|limb|foreleg|hindleg|frontleg|rearleg)([._-]|$)", re.I)
    for prefix, numbered in sorted(groups.items()):
        if not leg_hints.search(prefix):
            continue
        ordered = sorted(numbered)
        # Keep only a contiguous run from the first numbered bone.
        chain = [numbered[ordered[0]]]
        for number in ordered[1:]:
            prev_number = int(re.search(r"(\d+)$", chain[-1]).group(1))
            if number != prev_number + 1:
                break
            chain.append(numbered[number])
        if len(chain) < 2:
            continue
        hierarchy_ok = all(bones[chain[i]].parent and bones[chain[i]].parent.name == chain[i - 1]
                           for i in range(1, len(chain)))
        if not hierarchy_ok:
            continue
        leaf = chain[-1]
        legs.append({"name": prefix, "bones": chain, "contact_bone": leaf,
                     "side": "left" if re.search(r"(^|[._-])L($|[._-])", prefix, re.I) else
                             "right" if re.search(r"(^|[._-])R($|[._-])", prefix, re.I) else "unknown",
                     "confidence": "HIGH_NAME_AND_HIERARCHY",
                     "identity_confirmed": False})

    def role_bones(pattern: str) -> list[str]:
        rx = re.compile(pattern, re.I)
        return sorted(n for n in names if rx.search(n))

    wings = role_bones(r"wing|feather|flight")
    tails = role_bones(r"tail|caudal")
    heads = role_bones(r"head|neck|jaw")
    body = role_bones(r"body|spine|torso|pelvis|root")
    return {
        "schema_version": 2,
        "profile_name": armature.name + "_anatomy",
        "armature": armature.name,
        "bone_count": len(bones),
        "legs": legs,
        "leg_count": len(legs),
        "body_bones": body,
        "head_bones": heads,
        "wing_bones": wings,
        "tail_bones": tails,
        "mapping_status": "PROPOSAL_REQUIRES_USER_CONFIRMATION",
        "detection_method": "bone names plus verified contiguous parent hierarchy",
        "notes": ["Contact bone is a distal-chain proposal, not a verified sole region.",
                  "Confirm each limb identity and contact region before contact locking."],
    }
