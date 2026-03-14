# main.py — entry point

import sys
import threading

from PyQt6.QtWidgets import QApplication

from hid_layer import SpeedEditor, Key
import app as application
import config as cfg


def main():
    qt_app = QApplication(sys.argv)
    qt_app.setStyle("Fusion")

    window = application.MainWindow()
    window.show()

    config = window._config
    signals = window.get_signals()

    # Runtime layer stack — bottom is always default
    _layer_stack = [cfg.DEFAULT_LAYER_ID]

    def _current_layer():
        return _layer_stack[-1]

    def _push_layer(layer_id):
        _layer_stack.append(layer_id)
        signals.layer_runtime_changed.emit(layer_id)

    def _pop_layer():
        if len(_layer_stack) > 1:
            _layer_stack.pop()
        signals.layer_runtime_changed.emit(_current_layer())

    # Track which keys are currently held (avoid repeat firing)
    _held = set()

    def on_key(keys):
        nonlocal _held
        pressed = {k.name for k in keys}
        newly_pressed = pressed - _held
        _held = pressed
        for key_name in newly_pressed:
            signals.button_pressed.emit(key_name)
            application.dispatch(key_name, config, _current_layer(),
                                 on_push=_push_layer, on_pop=_pop_layer)
            window.refresh_button_colors()

    # Start HID listener in background thread
    se = SpeedEditor()

    def hid_thread():
        try:
            se.authenticate()
            se.on_key = on_key
            se.run()
        except Exception as e:
            print(f'[HID] Error: {e}')

    t = threading.Thread(target=hid_thread, daemon=True)
    t.start()

    exit_code = qt_app.exec()
    se.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
