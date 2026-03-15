# actions/system.py — system control (volume, brightness)
# Platform-specific implementations live in platform_layer/

from platform_layer import (
    VOL_STEP, BRIGHT_STEP,
    adjust_master_volume,
    adjust_app_volume,
    list_audio_apps,
    adjust_brightness,
)
