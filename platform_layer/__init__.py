# platform_layer/__init__.py
# Selects the correct platform implementation at import time.

import sys

if sys.platform == 'win32':
    from .windows import (
        VOL_STEP, BRIGHT_STEP,
        adjust_master_volume, adjust_app_volume, list_audio_apps,
        adjust_brightness,
        switch_to, list_windows,
        press_keys, release_keys,
        collect_installable_apps, launch_app,
    )
elif sys.platform == 'darwin':
    from .macos import (
        VOL_STEP, BRIGHT_STEP,
        adjust_master_volume, adjust_app_volume, list_audio_apps,
        adjust_brightness,
        switch_to, list_windows,
        press_keys, release_keys,
        collect_installable_apps, launch_app,
    )
else:
    raise RuntimeError(f'Unsupported platform: {sys.platform}')
