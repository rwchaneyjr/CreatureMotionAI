"""Reusable, scale-normalized stance/swing/uncertain state logic.

This module is deliberately independent of Blender and creature naming. Callers
provide an anatomically defined sole point, its world-space observation, and a
confidence derived from the actual contact geometry and motion evidence.
"""
from dataclasses import dataclass
from enum import Enum
from math import sqrt
from typing import Optional, Sequence, Tuple

Vec3 = Tuple[float, float, float]


class ContactState(str, Enum):
    STANCE = "STANCE"
    SWING = "SWING"
    UNCERTAIN = "UNCERTAIN"


@dataclass(frozen=True)
class ContactConfig:
    enter_clearance_ratio: float = 0.025
    exit_clearance_ratio: float = 0.065
    enter_speed_ratio: float = 0.045
    exit_speed_ratio: float = 0.11
    minimum_confidence: float = 0.55
    confirm_frames: int = 2

    def __post_init__(self):
        if not 0 <= self.enter_clearance_ratio < self.exit_clearance_ratio:
            raise ValueError("clearance thresholds must have entry < exit")
        if not 0 <= self.enter_speed_ratio < self.exit_speed_ratio:
            raise ValueError("speed thresholds must have entry < exit")
        if not 0 <= self.minimum_confidence <= 1 or self.confirm_frames < 1:
            raise ValueError("invalid confidence or confirmation-frame setting")


@dataclass(frozen=True)
class ContactDecision:
    state: ContactState
    confidence: float
    anchor_world: Optional[Vec3]
    lock_enabled: bool
    reason: str


def _vector(value: Sequence[float]) -> Vec3:
    if len(value) != 3:
        raise ValueError("contact positions must have three coordinates")
    return float(value[0]), float(value[1]), float(value[2])


def _distance(a: Sequence[float], b: Sequence[float]) -> float:
    return sqrt(sum((float(x) - float(y)) ** 2 for x, y in zip(a, b)))


def observation_confidence(clearance: float, speed_per_frame: float,
                           limb_length: float, anatomy_quality: float,
                           config: ContactConfig = ContactConfig()) -> float:
    """Combine geometric proximity, low motion, and sole-region quality.

    `anatomy_quality` is supplied by the caller (e.g. underside-normal and
    vertex-count checks); it is not inferred from a bone endpoint.
    """
    if limb_length <= 0 or anatomy_quality <= 0:
        return 0.0
    if clearance < -config.exit_clearance_ratio * limb_length:
        return 0.0
    h = max(0.0, min(1.0, 1.0 - max(0.0, clearance) /
                     (config.exit_clearance_ratio * limb_length)))
    v = max(0.0, min(1.0, 1.0 - max(0.0, speed_per_frame) /
                     (config.exit_speed_ratio * limb_length)))
    return max(0.0, min(1.0, float(anatomy_quality))) * sqrt(h * v)


class FootContactTracker:
    """Hysteretic contact state machine for one limb's world-space sole point."""

    def __init__(self, config: ContactConfig = ContactConfig()):
        self.config = config
        self.state = ContactState.UNCERTAIN
        self.anchor_world: Optional[Vec3] = None
        self._last_position: Optional[Vec3] = None
        self._last_frame: Optional[int] = None
        self._entry_count = 0

    def reset(self) -> None:
        self.state = ContactState.UNCERTAIN
        self.anchor_world = None
        self._last_position = None
        self._last_frame = None
        self._entry_count = 0

    def update(self, frame: int, sole_world: Optional[Sequence[float]],
               ground_clearance: Optional[float], limb_length: float,
               anatomy_quality: float = 1.0, observation_quality: float = 1.0,
               constraints_valid: bool = True) -> ContactDecision:
        if sole_world is None or ground_clearance is None or limb_length <= 0:
            return self._uncertain("missing_observation", None)
        position = _vector(sole_world)
        if (self._last_position is None or self._last_frame is None or
                frame != self._last_frame + 1):
            self._last_position, self._last_frame = position, int(frame)
            self._entry_count = 0
            return self._uncertain("velocity_not_observed", None)

        speed = _distance(position, self._last_position)
        self._last_position, self._last_frame = position, int(frame)
        confidence = observation_confidence(
            float(ground_clearance), speed, limb_length,
            min(float(anatomy_quality), float(observation_quality)), self.config)

        if not constraints_valid:
            return self._uncertain("lock_would_violate_constraints", confidence)
        if confidence < self.config.minimum_confidence:
            return self._uncertain("low_contact_confidence", confidence)

        enter_height = self.config.enter_clearance_ratio * limb_length
        exit_height = self.config.exit_clearance_ratio * limb_length
        enter_speed = self.config.enter_speed_ratio * limb_length
        exit_speed = self.config.exit_speed_ratio * limb_length

        if self.state == ContactState.STANCE:
            if ground_clearance > exit_height or speed > exit_speed:
                self.state = ContactState.SWING
                self.anchor_world = None
                self._entry_count = 0
                return ContactDecision(self.state, confidence, None, False,
                                       "stance_exit_threshold")
            return ContactDecision(self.state, confidence, self.anchor_world,
                                   True, "stance_anchor_retained")

        if ground_clearance <= enter_height and speed <= enter_speed:
            self._entry_count += 1
            if self._entry_count >= self.config.confirm_frames:
                self.state = ContactState.STANCE
                self.anchor_world = position
                return ContactDecision(self.state, confidence,
                                       self.anchor_world, True,
                                       "contact_confirmed")
            self.state = ContactState.SWING
            return ContactDecision(self.state, confidence, None, False,
                                   "contact_candidate_pending")

        self._entry_count = 0
        self.state = ContactState.SWING
        self.anchor_world = None
        return ContactDecision(self.state, confidence, None, False,
                               "lift_or_motion_detected")

    def _uncertain(self, reason: str, confidence: Optional[float]) -> ContactDecision:
        self.state = ContactState.UNCERTAIN
        self.anchor_world = None
        self._entry_count = 0
        return ContactDecision(self.state, float(confidence or 0.0), None,
                               False, reason)
