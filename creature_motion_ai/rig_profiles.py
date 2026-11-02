"""Reusable creature rig profiles and conservative armature inspection.

Profiles describe anatomy; they do not alter meshes, armatures, or actions.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class LegChain:
    name: str
    bones: tuple[str, ...]
    side: str = "center"
    station: int = 0


@dataclass(frozen=True)
class SkeletonProfile:
    name: str
    legs: tuple[LegChain, ...]
    heads: tuple[str, ...] = ()
    tails: tuple[str, ...] = ()
    wings: tuple[str, ...] = ()

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
