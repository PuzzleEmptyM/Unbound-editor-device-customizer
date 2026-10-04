"""Small, consistent pointer and wheel steps shared by every application.

``install(lambda: window._config)`` replaces the two desktop input functions.
Their legacy per-layer ``amount`` argument remains accepted, but the current
global preference controls distance. No timer or worker emits delayed motion.
Call ``reset()`` when a mouse mode is released to discard speed history.
"""
import math
import threading
import time

DEFAULTS = {'pointer_step': 2, 'scroll_step': 8, 'acceleration': True}
_provider = lambda: {}
_input = None
_lock = threading.RLock()
_clock = time.monotonic
_motion = None


def _bounded(value, default, minimum, maximum):
    if isinstance(value, bool):
        return default
    try:
        value = int(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return max(minimum, min(maximum, value))


def settings(config):
    """Return normalized global preferences without changing the config."""
    value = config
    for key in ('layers', 'default', 'context_switching', 'precision_input'):
        value = value.get(key, {}) if isinstance(value, dict) else {}
    if not isinstance(value, dict):
        value = {}
    acceleration = value.get('acceleration', DEFAULTS['acceleration'])
    return {
        'pointer_step': _bounded(value.get('pointer_step'), 2, 1, 12),
        'scroll_step': _bounded(value.get('scroll_step'), 8, 1, 40),
        'acceleration': acceleration if isinstance(acceleration, bool) else True,
    }


def reset():
    """Discard the previous motion's axis, direction, and speed history."""
    global _motion
    with _lock:
        _motion = None


def _sign(value):
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError):
        return 0
    if not math.isfinite(value):
        return 0
    return 1 if value > 0 else -1 if value < 0 else 0


def move(axis, direction, amount=12):
    """Emit one bounded step, with a gradual boost during fast repeated turns."""
    global _motion
    with _lock:
        sign = _sign(direction)
        if axis not in ('x', 'y') or not sign:
            reset()
            return
        prefs = settings(_provider())
        step = prefs['pointer_step']
        signature = (axis, sign, step, prefs['acceleration'])
        now = _clock()
        fast_turns = 0
        if _motion is not None and _motion[0] == signature:
            elapsed = now - _motion[1]
            if 0 <= elapsed < .06:
                fast_turns = min(8, _motion[2] + 1)
            elif .06 <= elapsed <= .18:
                # Ease back down instead of keeping the fast-turn boost.
                fast_turns = max(0, _motion[2] - 4)
        _motion = (signature, now, fast_turns)
        if prefs['acceleration']:
            step = min(12, step + min(2, fast_turns // 4))
        delta = sign * step
        _input.emit(1, delta if axis == 'x' else 0,
                    delta if axis == 'y' else 0)


def scroll(direction, amount=35):
    """Emit a small wheel delta; preserve the original knob direction."""
    with _lock:
        reset()
        sign = _sign(direction)
        if sign:
            _input.emit(0x800, data=-sign * settings(_provider())['scroll_step'])


def install(provider):
    """Use a live config provider for both common and application mouse modes."""
    global _provider, _input
    if not callable(provider):
        raise TypeError('precision input requires a config provider')
    import speed_editor_desktop_input as inputs
    with _lock:
        _provider = provider
        _input = inputs
        reset()
        inputs.move = move
        inputs.scroll = scroll
