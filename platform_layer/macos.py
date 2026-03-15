# platform_layer/macos.py — macOS-specific implementations
#
# Volume and brightness use osascript (no extra dependencies).
# Per-app volume is not yet implemented (requires CoreAudio bindings).
# Window management uses osascript / AppKit.

import os
import subprocess

VOL_STEP    = 0.02   # 2 % per jog tick (expressed as 0–1 fraction)
BRIGHT_STEP = 5      # 5 % per jog tick


# ---------------------------------------------------------------------------
# Volume
# ---------------------------------------------------------------------------

def adjust_master_volume(delta: float):
    """Raise or lower master volume. delta is a fraction (e.g. 0.02 = 2%)."""
    try:
        result = subprocess.run(
            ['osascript', '-e', 'output volume of (get volume settings)'],
            capture_output=True, text=True
        )
        current = int(result.stdout.strip())
        new_vol = max(0, min(100, current + round(delta * 100)))
        subprocess.run(['osascript', '-e', f'set volume output volume {new_vol}'], check=True)
    except Exception as e:
        print(f'[volume] {e}')


def adjust_app_volume(app_name: str, delta: float):
    """Per-app volume is not yet implemented on macOS."""
    print(f'[app_volume] per-app volume not yet implemented on macOS')


def list_audio_apps() -> list[str]:
    """Per-app audio session listing not yet implemented on macOS."""
    return []


# ---------------------------------------------------------------------------
# Brightness
# ---------------------------------------------------------------------------

def adjust_brightness(delta: int):
    """Raise or lower display brightness by delta percent."""
    try:
        import screen_brightness_control as sbc
        current = sbc.get_brightness(display=0)
        if isinstance(current, list):
            current = current[0]
        sbc.set_brightness(max(0, min(100, current + delta)), display=0)
    except Exception as e:
        print(f'[brightness] {e}')


# ---------------------------------------------------------------------------
# Window management
# ---------------------------------------------------------------------------

def switch_to(app_name: str) -> bool:
    """Bring an app matching app_name to the foreground via osascript."""
    try:
        # Try exact app name first, then search running processes
        script = f'tell application "{app_name}" to activate'
        result = subprocess.run(['osascript', '-e', script], capture_output=True)
        if result.returncode == 0:
            return True
        # Fallback: search by process name via System Events
        script = (
            f'tell application "System Events"\n'
            f'  set procs to every process whose name contains "{app_name}"\n'
            f'  if procs is not {{}} then\n'
            f'    set frontmost of item 1 of procs to true\n'
            f'  end if\n'
            f'end tell'
        )
        subprocess.run(['osascript', '-e', script], check=True)
        return True
    except Exception as e:
        print(f'[app_switch] {e}')
        return False


def list_windows() -> list[str]:
    """Return names of visible running applications via osascript."""
    try:
        script = (
            'tell application "System Events"\n'
            '  get name of every process whose visible is true\n'
            'end tell'
        )
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
        names = [n.strip() for n in result.stdout.strip().split(',') if n.strip()]
        return sorted(names)
    except Exception as e:
        print(f'[list_windows] {e}')
        return []


# ---------------------------------------------------------------------------
# Key hold / release — use pynput (cross-platform, no VK codes needed)
# ---------------------------------------------------------------------------

from pynput.keyboard import Controller as _Controller, Key as _PKey

_keyboard = _Controller()

_SPECIAL_KEYS = {
    "ctrl":   _PKey.ctrl,   "shift": _PKey.shift,  "alt":   _PKey.alt,
    "win":    _PKey.cmd,    "enter": _PKey.enter,   "space": _PKey.space,
    "tab":    _PKey.tab,    "esc":   _PKey.esc,
    "up":     _PKey.up,     "down":  _PKey.down,
    "left":   _PKey.left,   "right": _PKey.right,
    "delete": _PKey.delete, "backspace": _PKey.backspace,
    "home":   _PKey.home,   "end":   _PKey.end,
    "page_up": _PKey.page_up, "page_down": _PKey.page_down,
    "f1":  _PKey.f1,  "f2":  _PKey.f2,  "f3":  _PKey.f3,  "f4":  _PKey.f4,
    "f5":  _PKey.f5,  "f6":  _PKey.f6,  "f7":  _PKey.f7,  "f8":  _PKey.f8,
    "f9":  _PKey.f9,  "f10": _PKey.f10, "f11": _PKey.f11, "f12": _PKey.f12,
}


def _parse_keys(hotkey_str: str):
    keys = []
    for part in hotkey_str.lower().split('+'):
        part = part.strip()
        if part in _SPECIAL_KEYS:
            keys.append(_SPECIAL_KEYS[part])
        elif len(part) == 1:
            keys.append(part)
    return keys


def press_keys(hotkey_str: str):
    """Hold keys down via pynput."""
    keys = _parse_keys(hotkey_str)
    print(f'[hold] press  {hotkey_str!r}')
    for k in keys:
        _keyboard.press(k)


def release_keys(hotkey_str: str):
    """Release held keys via pynput."""
    keys = _parse_keys(hotkey_str)
    print(f'[hold] release {hotkey_str!r}')
    for k in reversed(keys):
        _keyboard.release(k)


# ---------------------------------------------------------------------------
# App picker — /Applications bundles
# ---------------------------------------------------------------------------

def collect_installable_apps() -> list[tuple[str, str]]:
    """Return [(display_name, app_path), ...] from /Applications."""
    import glob as _glob
    folders = ['/Applications', os.path.expanduser('~/Applications')]
    apps = {}
    for folder in folders:
        for app in _glob.glob(os.path.join(folder, '*.app')):
            name = os.path.splitext(os.path.basename(app))[0]
            if name not in apps:
                apps[name] = app
        # One level deep (e.g. /Applications/Utilities/*.app)
        for app in _glob.glob(os.path.join(folder, '*', '*.app')):
            name = os.path.splitext(os.path.basename(app))[0]
            if name not in apps:
                apps[name] = app
    return sorted(apps.items(), key=lambda x: x[0].lower())


# ---------------------------------------------------------------------------
# App launch
# ---------------------------------------------------------------------------

def launch_app(path: str):
    """Launch an app bundle, file, or URI via the macOS 'open' command."""
    subprocess.Popen(['open', path])
