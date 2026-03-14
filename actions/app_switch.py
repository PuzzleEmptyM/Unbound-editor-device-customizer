# actions/app_switch.py — switch focus to a running window by name

import win32gui
import win32con


def _find_window(app_name: str):
    """Find the first window whose title contains app_name (case-insensitive)."""
    app_lower = app_name.lower()
    result = None

    def callback(hwnd, _):
        nonlocal result
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd).lower()
            if app_lower in title:
                result = hwnd
        return True

    win32gui.EnumWindows(callback, None)
    return result


def switch_to(app_name: str) -> bool:
    """Bring a window matching app_name to the foreground. Returns True on success."""
    hwnd = _find_window(app_name)
    if not hwnd:
        return False
    # Restore if minimised
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(hwnd)
    return True


def list_windows() -> list[str]:
    """Return titles of all visible top-level windows (for the UI picker)."""
    titles = []

    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:
                titles.append(title)
        return True

    win32gui.EnumWindows(callback, None)
    return sorted(titles)
