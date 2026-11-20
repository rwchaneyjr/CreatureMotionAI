"""Small regression checks for reusable stance hysteresis and anchor behavior."""
from creature_motion_ai.contact_states import ContactState, FootContactTracker


def test_stance_anchor_hysteresis_and_release():
    tracker = FootContactTracker()
    # First sample establishes velocity history; the next two confirm contact.
    assert tracker.update(1, (0, 0, 0), 0.001, 1.0).state == ContactState.UNCERTAIN
    assert tracker.update(2, (0, 0, 0), 0.001, 1.0).state == ContactState.SWING
    planted = tracker.update(3, (0, 0, 0), 0.001, 1.0)
    assert planted.state == ContactState.STANCE and planted.lock_enabled
    assert planted.anchor_world == (0.0, 0.0, 0.0)
    retained = tracker.update(4, (0.01, 0, 0), 0.03, 1.0)
    assert retained.state == ContactState.STANCE
    assert retained.anchor_world == planted.anchor_world
    released = tracker.update(5, (0.2, 0, 0), 0.08, 1.0)
    assert released.state in {ContactState.SWING, ContactState.UNCERTAIN}
    assert not released.lock_enabled and released.anchor_world is None


def test_uncertain_observation_releases_lock():
    tracker = FootContactTracker()
    tracker.update(1, (0, 0, 0), 0.0, 1.0)
    tracker.update(2, (0, 0, 0), 0.0, 1.0)
    assert tracker.update(3, (0, 0, 0), 0.0, 1.0).state == ContactState.STANCE
    uncertain = tracker.update(4, None, None, 1.0)
    assert uncertain.state == ContactState.UNCERTAIN
    assert uncertain.anchor_world is None


if __name__ == "__main__":
    test_stance_anchor_hysteresis_and_release()
    test_uncertain_observation_releases_lock()
    print("contact-state checks: PASS")
