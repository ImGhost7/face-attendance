"""Active liveness: ask the person to turn their head a random way, check the pose really changes.

Stops the laziest attack (holding up a still photo). It does NOT stop a pre-recorded video of the
right person turning their head - that needs a depth/IR camera or a trained anti-spoof model
(planned: Phase 6, evaluate MiniFASNet-style passive liveness, Apache-2.0).
"""
import random
import time

from .quality import estimate_pose


class HeadTurnChallenge:
    """Directions are in IMAGE coordinates (the kiosk UI mirrors its wording for the user)."""

    CENTER = 0.12
    TURNED = 0.25

    def __init__(self, direction: str | None = None, timeout_s: float = 6.0, rng: random.Random | None = None, clock=time.monotonic):
        self.direction = direction or (rng or random).choice(["image_left", "image_right"])
        self.timeout_s = timeout_s
        self._clock = clock
        self._t0 = clock()
        self._seen_center = False
        self.passed = False

    @property
    def expired(self) -> bool:
        return not self.passed and (self._clock() - self._t0) > self.timeout_s

    def update(self, landmarks) -> bool:
        """Feed landmarks of the SAME tracked face each frame. Returns True once passed."""
        if self.passed or self.expired:
            return self.passed
        yaw, _ = estimate_pose(landmarks)
        if abs(yaw) <= self.CENTER:
            self._seen_center = True
        want = yaw >= self.TURNED if self.direction == "image_right" else yaw <= -self.TURNED
        if self._seen_center and want:
            self.passed = True
        return self.passed
