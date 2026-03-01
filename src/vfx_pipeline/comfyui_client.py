"""ComfyUI HTTP/WebSocket client for workflow submission and monitoring."""

import json
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.request import urlopen, Request
from urllib.error import URLError
from urllib.parse import urlencode


class ComfyUIClient:
    """Minimal ComfyUI API client — no external deps required."""

    def __init__(self, base_url: str = "http://comfyui:8188"):
        self.base_url = base_url.rstrip("/")
        self.client_id = str(uuid.uuid4())

    def _get(self, path: str) -> Any:
        url = f"{self.base_url}{path}"
        with urlopen(url, timeout=30) as resp:
            return json.loads(resp.read())

    def _post(self, path: str, data: dict) -> Any:
        url = f"{self.base_url}{path}"
        body = json.dumps(data).encode()
        req = Request(url, data=body, headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())

    def system_stats(self) -> dict:
        return self._get("/system_stats")

    def free_memory(self) -> None:
        """Unload all models and free GPU memory."""
        url = f"{self.base_url}/free"
        body = json.dumps({"unload_models": True, "free_memory": True}).encode()
        req = Request(url, data=body, headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=60) as resp:
            resp.read()  # may return empty body

    def upload_image(self, filepath: str, subfolder: str = "") -> str:
        """Upload an image to ComfyUI input directory."""
        import mimetypes
        from urllib.request import urlopen, Request

        boundary = uuid.uuid4().hex
        filename = Path(filepath).name
        content_type = mimetypes.guess_type(filepath)[0] or "application/octet-stream"

        with open(filepath, "rb") as f:
            file_data = f.read()

        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode() + file_data + (
            f"\r\n--{boundary}\r\n"
            f'Content-Disposition: form-data; name="subfolder"\r\n\r\n'
            f"{subfolder}\r\n"
            f"--{boundary}--\r\n"
        ).encode()

        req = Request(
            f"{self.base_url}/upload/image",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        with urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
        return result.get("name", filename)

    def submit_workflow(self, workflow: dict) -> str:
        """Submit a workflow and return the prompt_id."""
        payload = {"prompt": workflow, "client_id": self.client_id}
        result = self._post("/prompt", payload)
        return result["prompt_id"]

    def get_history(self, prompt_id: str) -> dict:
        return self._get(f"/history/{prompt_id}")

    def wait_for_completion(
        self, prompt_id: str, poll_interval: float = 3.0, timeout: float = 600.0
    ) -> dict:
        """Poll until workflow completes or fails. Returns outputs dict."""
        start = time.time()
        while time.time() - start < timeout:
            history = self.get_history(prompt_id)
            entry = history.get(prompt_id)
            if entry:
                status = entry.get("status", {})
                if status.get("completed"):
                    return entry.get("outputs", {})
                status_str = status.get("status_str", "")
                if status_str == "error":
                    raise RuntimeError(f"Workflow failed: {json.dumps(status)}")
            time.sleep(poll_interval)
        raise TimeoutError(f"Workflow {prompt_id} did not complete in {timeout}s")

    def run_workflow(self, workflow: dict, timeout: float = 600.0) -> dict:
        """Submit workflow and wait for outputs."""
        prompt_id = self.submit_workflow(workflow)
        print(f"  Submitted workflow: {prompt_id}")
        return self.wait_for_completion(prompt_id, timeout=timeout)

    def get_output_path(self, outputs: dict, node_id: str, key: str = "images") -> str:
        """Extract output file path from workflow outputs."""
        node_out = outputs.get(node_id, {})
        items = node_out.get(key, [])
        if items:
            item = items[0]
            subfolder = item.get("subfolder", "")
            filename = item.get("filename", "")
            if subfolder:
                return f"{subfolder}/{filename}"
            return filename
        # Check for 'result' key (SAM3D nodes use this)
        results = node_out.get("result", [])
        if results:
            return results[0]
        return ""
