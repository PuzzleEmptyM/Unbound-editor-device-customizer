# Blackmagic Speed Editor Customizer

A desktop app for remapping the buttons on a Blackmagic Design Speed Editor to anything you want, without needing DaVinci Resolve open.

## Features

**Button actions**

- **Hotkey** — tap a key combination (e.g. `ctrl+shift+s`)
- **Hold Key** — hold a modifier key down for as long as the Speed Editor button is physically held
- **Toggle Hold** — latch a modifier key down on first press, release it on second press. Useful for alt+scroll in Resolve.
- **App Switch** — bring any open window to focus by title substring
- **OBS: Switch Scene** — switch to a named OBS scene
- **OBS: Toggle Stream / Record / Mute Mic** — toggle OBS outputs

**Layer system**

Layers are like presets. Each layer has its own set of button mappings. You can map a button to "Layer: Push" to switch all bindings to another layer, and the same button is automatically assigned as "Layer: Back" on the target layer so you can never get stuck.

Layers appear as tabs at the top of the Buttons view. The active layer is marked with a triangle. When the physical device switches layers, the app follows automatically.

**Device connection**

The app connects to the Speed Editor over Bluetooth without DaVinci Resolve running. It handles the proprietary challenge-response authentication on its own and re-authenticates automatically before the session times out.

If the device is not available at startup (e.g. Resolve is using it), the app retries every 3 seconds in the background. The status bar shows the current connection state.

## Requirements

- Windows 10 or 11
- Python 3.12 (managed via `uv`)
- Blackmagic Design Speed Editor connected over Bluetooth
- OBS Studio with WebSocket server enabled (optional, for OBS actions)

## Setup

```
uv venv
uv pip install PyQt6 hid pynput pywin32 obsws-python
```

Then run:

```
uv run main.py
```

## Usage with DaVinci Resolve

The recommended workflow is to not use Resolve's built-in Speed Editor integration at all. Instead:

1. Map Speed Editor buttons to keyboard shortcuts in this app
2. Configure those same shortcuts in Resolve under Keyboard Customization

This way Resolve sees standard keyboard input and the Speed Editor is fully under your control.

If Resolve steals the device connection, quit and relaunch this app while Resolve is already open. The app will connect and authenticate without interfering with Resolve's session.

## Using Toggle Hold for modifier+scroll

1. Map a button to **Toggle Hold** and enter `alt` (or `ctrl`, `shift`, etc.)
2. Press the button once to latch the modifier key down
3. Scroll your mouse wheel in Resolve (or any app)
4. Press the button again to release the modifier

To verify the latch is active before testing scroll, press Tab on your physical keyboard. If Alt+Tab triggers, the modifier is held correctly.

## File structure

| File | Purpose |
|------|---------|
| `main.py` | Entry point, HID thread, layer stack, toggle hold state |
| `app.py` | PyQt6 GUI, action panel, layer tabs, button grid |
| `config.py` | Load/save config.json, layer management helpers |
| `hid_layer.py` | Speed Editor HID abstraction and authentication |
| `actions/hotkey.py` | Keyboard event sending via pynput and win32api |
| `actions/app_switch.py` | Window focus via pywin32 |
| `actions/obs.py` | OBS WebSocket client via obsws-python |
| `config.json` | Your saved button mappings (auto-created) |

## Authentication

The Speed Editor requires a challenge-response handshake before it sends input events. The algorithm was reverse-engineered by Sylvain Munaut (Apache 2.0) and is reproduced in `hid_layer.py`. The app authenticates on connect and schedules a re-auth timer before the session expires.

## Credits

HID authentication algorithm by [Sylvain Munaut](https://github.com/smunaut) (Apache 2.0).
