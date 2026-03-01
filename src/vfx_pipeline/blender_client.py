"""Blender MCP WebSocket client for remote Blender control."""

import json
import time
from typing import Any, Optional


class BlenderClient:
    """WebSocket client for the Unified Blender MCP addon."""

    def __init__(self, url: str = "ws://127.0.0.1:8765"):
        self.url = url
        self._ws = None
        self._msg_id = 0

    def connect(self):
        import websocket
        self._ws = websocket.create_connection(self.url, timeout=30)
        return self

    def close(self):
        if self._ws:
            self._ws.close()
            self._ws = None

    def __enter__(self):
        return self.connect()

    def __exit__(self, *args):
        self.close()

    def _next_id(self) -> str:
        self._msg_id += 1
        return f"msg_{self._msg_id}"

    def call_tool(self, tool: str, params: Optional[dict] = None, timeout: int = 120) -> dict:
        """Call a Blender MCP tool and return the result."""
        if not self._ws:
            self.connect()

        msg_id = self._next_id()
        payload = {"id": msg_id, "tool": tool, "params": params or {}}
        self._ws.send(json.dumps(payload))

        old_timeout = self._ws.gettimeout()
        self._ws.settimeout(timeout)
        try:
            raw = self._ws.recv()
        finally:
            self._ws.settimeout(old_timeout)

        result = json.loads(raw)
        if result.get("status") == "error":
            raise RuntimeError(f"Blender tool '{tool}' failed: {result.get('error', result)}")
        return result

    def execute_python(self, code: str, timeout: int = 300) -> dict:
        """Execute Python code in Blender and return the result."""
        result = self.call_tool("execute_python", {"code": code}, timeout=timeout)
        data = result.get("data", {}).get("data", {})
        stdout = data.get("stdout", "")
        if stdout:
            print(f"  [Blender] {stdout.strip()}")
        return data

    def get_scene_info(self) -> dict:
        result = self.call_tool("get_scene_info")
        return result.get("data", {}).get("data", {})

    def import_model(self, filepath: str, **kwargs) -> dict:
        params = {"filepath": filepath}
        params.update(kwargs)
        return self.call_tool("import_model", params, timeout=60)

    def render_animation(self, output_path: str, fmt: str = "FFMPEG") -> dict:
        return self.call_tool(
            "render_animation",
            {"output_path": output_path, "format": fmt},
            timeout=600,
        )

    def set_render_settings(self, **kwargs) -> dict:
        return self.call_tool("set_render_settings", kwargs)
