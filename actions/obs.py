# actions/obs.py — OBS WebSocket control

import threading
import obsws_python as obs


class OBSClient:
    def __init__(self):
        self._client = None
        self._lock = threading.Lock()

    def connect(self, host: str, port: int, password: str) -> bool:
        try:
            with self._lock:
                if self._client:
                    try:
                        self._client.disconnect()
                    except Exception:
                        pass
                self._client = obs.ReqClient(host=host, port=port, password=password, timeout=5)
            return True
        except Exception as e:
            print(f'[OBS] Connection failed: {e}')
            self._client = None
            return False

    def disconnect(self):
        with self._lock:
            if self._client:
                try:
                    self._client.disconnect()
                except Exception:
                    pass
                self._client = None

    def is_connected(self) -> bool:
        return self._client is not None

    def get_scenes(self) -> list[str]:
        try:
            with self._lock:
                result = self._client.get_scene_list()
            return [s['sceneName'] for s in result.scenes]
        except Exception:
            return []

    def switch_scene(self, scene_name: str):
        try:
            with self._lock:
                self._client.set_current_program_scene(scene_name)
        except Exception as e:
            print(f'[OBS] Scene switch failed: {e}')

    def toggle_stream(self):
        try:
            with self._lock:
                self._client.toggle_stream()
        except Exception as e:
            print(f'[OBS] Toggle stream failed: {e}')

    def toggle_record(self):
        try:
            with self._lock:
                self._client.toggle_record()
        except Exception as e:
            print(f'[OBS] Toggle record failed: {e}')

    def toggle_mute_mic(self):
        """Toggle mute on the first input whose name contains 'mic' (case-insensitive)."""
        try:
            with self._lock:
                inputs = self._client.get_input_list()
            for inp in inputs.inputs:
                if 'mic' in inp['inputName'].lower():
                    with self._lock:
                        self._client.toggle_input_mute(inp['inputName'])
                    return
            print('[OBS] No mic input found')
        except Exception as e:
            print(f'[OBS] Toggle mute failed: {e}')


# Shared singleton used by the rest of the app
client = OBSClient()
