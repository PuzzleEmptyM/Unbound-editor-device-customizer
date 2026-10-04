"""Reliable foreground identity and responsive profile updates; no input or config writes."""
import ctypes, ntpath, queue, time
from ctypes import wintypes
import speed_editor_foreground as foreground_module
import speed_editor_context as context
from speed_editor_context_templates import BROWSERS, is_shorts

HOSTS = {'applicationframehost.exe'}
_installed = False
_original_foreground = foreground_module.foreground


def _process_identity(pid):
    """Resolve a PID directly, with a name-only fallback for protected processes."""
    if not pid:
        return '', ''
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    handle = kernel.OpenProcess(0x1000, False, int(pid))
    if handle:
        try:
            path = ctypes.create_unicode_buffer(32768)
            length = wintypes.DWORD(len(path))
            if kernel.QueryFullProcessImageNameW(handle, 0, path, ctypes.byref(length)):
                return path.value, ntpath.basename(path.value).casefold()
        finally:
            kernel.CloseHandle(handle)
    # Do not cache PID results: Windows can reuse the PID after an application exits.
    class ProcessEntry(ctypes.Structure):
        _fields_ = [('dwSize', wintypes.DWORD), ('cntUsage', wintypes.DWORD),
                    ('th32ProcessID', wintypes.DWORD), ('th32DefaultHeapID', ctypes.c_size_t),
                    ('th32ModuleID', wintypes.DWORD), ('cntThreads', wintypes.DWORD),
                    ('th32ParentProcessID', wintypes.DWORD), ('pcPriClassBase', wintypes.LONG),
                    ('dwFlags', wintypes.DWORD), ('szExeFile', wintypes.WCHAR * 260)]
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    for name in ('Process32FirstW', 'Process32NextW'):
        getattr(kernel, name).argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry)]
        getattr(kernel, name).restype = wintypes.BOOL
    handle = kernel.CreateToolhelp32Snapshot(2, 0)
    if handle == ctypes.c_void_p(-1).value:
        return '', ''
    try:
        entry = ProcessEntry(); entry.dwSize = ctypes.sizeof(entry)
        available = kernel.Process32FirstW(handle, ctypes.byref(entry))
        for _ in range(8192):
            if not available:
                break
            if entry.th32ProcessID == pid:
                return '', ntpath.basename(entry.szExeFile).casefold()
            available = kernel.Process32NextW(handle, ctypes.byref(entry))
    finally:
        kernel.CloseHandle(handle)
    return '', ''


def _visible_children(hwnd):
    user = ctypes.WinDLL('user32', use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user.EnumChildWindows.argtypes = [wintypes.HWND, callback_type, wintypes.LPARAM]
    user.IsWindowVisible.argtypes = [wintypes.HWND]
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    rows = []
    def collect(child, unused):
        if len(rows) >= 128:
            return False
        if user.IsWindowVisible(child):
            pid = wintypes.DWORD(); rect = wintypes.RECT()
            user.GetWindowThreadProcessId(child, ctypes.byref(pid))
            if user.GetWindowRect(child, ctypes.byref(rect)):
                area = max(0, rect.right - rect.left) * max(0, rect.bottom - rect.top)
                if area:
                    rows.append((area, pid.value))
        return True
    user.EnumChildWindows(hwnd, callback_type(collect), 0)
    return rows


def resolve_snapshot(snapshot, lookup=_process_identity, children=_visible_children):
    result = dict(snapshot)
    process = ntpath.basename(str(result.get('process') or '').strip(' "')).casefold()
    if not process and result.get('pid'):
        result['path'], process = lookup(result['pid'])
    result['process'] = process
    if process not in HOSTS:
        return result
    seen = {result.get('pid')}
    for area, pid in sorted(children(result['hwnd']), reverse=True):
        if pid in seen:
            continue
        seen.add(pid)
        path, name = lookup(pid)
        if name and name not in HOSTS and name not in {'explorer.exe', 'runtimebroker.exe', 'shellexperiencehost.exe'}:
            result.update(host_pid=result.get('pid'), host_process=process, pid=pid, path=path, process=name)
            break
    return result


def foreground():
    snapshot = _original_foreground()
    try:
        return resolve_snapshot(snapshot)
    except (OSError, ValueError, TypeError):
        return snapshot


def same_window(first, second):
    return all(first.get(k) == second.get(k) for k in ('hwnd', 'pid', 'process'))


def poll(monitor, accessibility):
    """Publish app changes before slow URL inspection, and reject old-page results."""
    snapshot = monitor.read()
    # Browser URLs are inspected on the worker. Keep the last verified route until
    # this same browser window is inspected again, avoiding a Chrome/YouTube flash.
    if snapshot.get('process') not in BROWSERS or not same_window(snapshot, monitor.latest):
        if not monitor.stop_event.is_set():
            monitor.on_snapshot(snapshot)
    inspected = dict(snapshot)
    if accessibility:
        try:
            inspected = accessibility.inspect(inspected)
        except Exception:
            pass
    current = monitor.read()
    if monitor.stop_event.is_set() or not same_window(current, snapshot):
        return
    # A title changing while UIA reads can mean a different tab. Do not attach
    # that URL to the new page, but still publish the new process/title promptly.
    if current.get('title') != snapshot.get('title'):
        monitor.latest = current
        monitor.on_snapshot(current)
    else:
        monitor.latest = inspected
        monitor.on_snapshot(inspected)


def run(monitor):
    accessibility = None
    try:
        try:
            accessibility = foreground_module.Accessibility()
        except Exception:
            monitor.on_notice('目前使用視窗標題辨識；播放器快捷鍵請先點選影片。')
        last_read = 0
        while not monitor.stop_event.is_set():
            now = time.monotonic()
            if now - last_read >= .25:
                try:
                    poll(monitor, accessibility)
                except (OSError, ValueError, TypeError):
                    pass
                last_read = now
            try:
                created, expected, keys, send, needs_focus = monitor.commands.get(timeout=.05)
            except queue.Empty:
                continue
            try:
                fresh = monitor.fast_snapshot()
            except Exception:
                continue
            if (time.monotonic() - created > .6 or monitor.classify(fresh) != 'youtube'
                    or any(fresh.get(k) != expected.get(k) for k in ('hwnd', 'pid', 'title'))):
                continue
            focused = False
            shorts_navigation = is_shorts(fresh) and keys in ('shift+p', 'shift+n')
            if shorts_navigation:
                keys = 'up' if keys == 'shift+p' else 'down'
            elif is_shorts(fresh):
                if keys in ('j', 'l'):
                    keys = 'left' if keys == 'j' else 'right'
                elif keys in ('up', 'down'):
                    keys = 'media_volume_up' if keys == 'up' else 'media_volume_down'; needs_focus = False
                elif keys in ('shift+,', 'shift+.'):
                    monitor.on_notice('目前 YouTube Shorts 未提供速度快捷鍵；請改在一般影片頁面調整速度。'); continue
                elif keys in list('0123456789'):
                    monitor.on_notice('Shorts 請用旋鈕進度或倒退／前進鍵；此頁面未提供百分比跳轉快捷鍵。'); continue
            if accessibility and needs_focus:
                try:
                    focused = accessibility.focus_page(fresh) if shorts_navigation else accessibility.focus_player({**fresh, '_player_keys': keys})
                except Exception:
                    pass
            if needs_focus and not focused and fresh.get('focus_edit'):
                monitor.on_notice('正在輸入文字；請先點選影片，再操作播放、音量或進度。'); continue
            try:
                current = monitor.read()
            except Exception:
                continue
            if monitor.stop_event.is_set() or any(current.get(k) != fresh.get(k) for k in ('hwnd', 'pid', 'title')):
                continue
            try:
                send(keys)
            except Exception:
                monitor.on_notice('這次播放控制未完成，請重新選取播放器後再試。')
    finally:
        if accessibility:
            try:
                accessibility.close()
            except Exception:
                pass


def install():
    global _installed
    if _installed:
        return
    _installed = True
    old_init = foreground_module.ForegroundMonitor.__init__
    def init(monitor, on_snapshot, on_notice, read=None, classifier=foreground_module.classify):
        old_init(monitor, on_snapshot, on_notice, read=read or foreground, classifier=classifier)
    foreground_module.foreground = foreground
    foreground_module.ForegroundMonitor.__init__ = init
    foreground_module.ForegroundMonitor._run = run
    old_detect = context.ContextController.detect
    def detect(controller, snapshot):
        snapshot = dict(snapshot)
        snapshot['process'] = ntpath.basename(str(snapshot.get('process') or '').strip(' "')).casefold()
        # Missing process metadata is temporary; keep the last valid route instead
        # of briefly assigning unrelated applications to the generic template.
        if not snapshot['process']:
            return None
        return old_detect(controller, snapshot)
    context.ContextController.detect = detect
