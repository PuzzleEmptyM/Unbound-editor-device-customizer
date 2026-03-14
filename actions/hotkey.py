# actions/hotkey.py — send keyboard shortcuts

from pynput.keyboard import Controller, Key as PKey

_keyboard = Controller()

# Map friendly names to pynput special keys
SPECIAL_KEYS = {
    "ctrl":   PKey.ctrl,
    "shift":  PKey.shift,
    "alt":    PKey.alt,
    "win":    PKey.cmd,
    "enter":  PKey.enter,
    "space":  PKey.space,
    "tab":    PKey.tab,
    "esc":    PKey.esc,
    "up":     PKey.up,
    "down":   PKey.down,
    "left":   PKey.left,
    "right":  PKey.right,
    "f1":     PKey.f1,  "f2":  PKey.f2,  "f3":  PKey.f3,  "f4":  PKey.f4,
    "f5":     PKey.f5,  "f6":  PKey.f6,  "f7":  PKey.f7,  "f8":  PKey.f8,
    "f9":     PKey.f9,  "f10": PKey.f10, "f11": PKey.f11, "f12": PKey.f12,
    "delete": PKey.delete, "backspace": PKey.backspace, "home": PKey.home,
    "end":    PKey.end, "page_up": PKey.page_up, "page_down": PKey.page_down,
    "media_play_pause": PKey.media_play_pause,
    "media_next":       PKey.media_next,
    "media_previous":   PKey.media_previous,
    "media_volume_up":  PKey.media_volume_up,
    "media_volume_down":PKey.media_volume_down,
    "media_volume_mute":PKey.media_volume_mute,
}


def parse_hotkey(hotkey_str: str):
    """Parse 'ctrl+shift+s' into a list of pynput key objects."""
    parts = [p.strip().lower() for p in hotkey_str.split('+')]
    keys = []
    for p in parts:
        if p in SPECIAL_KEYS:
            keys.append(SPECIAL_KEYS[p])
        elif len(p) == 1:
            keys.append(p)
    return keys


def send(hotkey_str: str):
    """Press and release a hotkey combination like 'ctrl+shift+s'."""
    keys = parse_hotkey(hotkey_str)
    if not keys:
        return
    # Press all keys in order
    for k in keys:
        _keyboard.press(k)
    # Release in reverse order
    for k in reversed(keys):
        _keyboard.release(k)
