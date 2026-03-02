"""Output validation between pipeline steps.

Each validator checks that a step produced usable output before
the pipeline advances. Returns (ok, message) tuples.
"""

import json
import os
import struct
from pathlib import Path
from typing import Optional


def validate_glb(path: str) -> tuple[bool, str]:
    """Check GLB file exists, has valid glTF header, and reasonable size."""
    if not path:
        return False, "GLB path is empty"

    p = Path(path)
    if not p.exists():
        return False, f"GLB file not found: {path}"

    size = p.stat().st_size
    if size < 100:
        return False, f"GLB file too small ({size} bytes): {path}"

    # Check glTF binary header (magic: 'glTF', version: 2)
    with open(path, "rb") as f:
        header = f.read(12)
        if len(header) < 12:
            return False, f"GLB file truncated ({len(header)} bytes header)"
        magic = header[:4]
        if magic != b"glTF":
            return False, f"Invalid GLB magic: {magic!r} (expected b'glTF')"
        version = struct.unpack("<I", header[4:8])[0]
        if version != 2:
            return False, f"Unsupported glTF version: {version} (expected 2)"

    return True, f"Valid GLB: {size:,} bytes, glTF v2"


def validate_scene_setup(blender_result: str) -> tuple[bool, str]:
    """Check Blender scene setup by parsing RESULT: line from script output."""
    if not blender_result:
        return False, "No Blender result returned"

    # Look for RESULT: line in stdout
    if "ERROR:" in blender_result:
        error_line = [l for l in blender_result.split("\n") if "ERROR:" in l]
        return False, f"Blender error: {error_line[0] if error_line else blender_result}"

    if "RESULT:" in blender_result:
        return True, blender_result.split("RESULT:")[-1].strip()

    return True, "Scene setup completed (no structured result)"


def validate_tracking(blender_result: str, min_keyframes: int = 2) -> tuple[bool, str]:
    """Check tracking produced enough keyframes."""
    if not blender_result:
        return False, "No tracking result returned"

    if "ERROR:" in blender_result:
        error_line = [l for l in blender_result.split("\n") if "ERROR:" in l]
        return False, f"Tracking error: {error_line[0] if error_line else blender_result}"

    # Parse keyframe count from RESULT line
    if "RESULT:" in blender_result:
        result_str = blender_result.split("RESULT:")[-1].strip()
        parts = dict(kv.split("=") for kv in result_str.split(",") if "=" in kv)
        kf_count = int(parts.get("keyframes", "0"))
        if kf_count < min_keyframes:
            return False, f"Too few keyframes: {kf_count} (minimum: {min_keyframes})"
        return True, f"Tracked: {kf_count} keyframes"

    return True, "Tracking completed (no structured result)"


def validate_composite_output(output_dir: str, expected_frames: Optional[int] = None) -> tuple[bool, str]:
    """Check composited PNG frames exist in output directory."""
    p = Path(output_dir)
    if not p.exists():
        return False, f"Output directory not found: {output_dir}"

    pngs = sorted(p.glob("composited_*.png"))
    if not pngs:
        return False, f"No composited frames in {output_dir}"

    if expected_frames and len(pngs) < expected_frames * 0.9:
        return False, f"Missing frames: {len(pngs)}/{expected_frames} ({output_dir})"

    # Check first frame is valid PNG (header check)
    with open(pngs[0], "rb") as f:
        header = f.read(8)
        if header[:4] != b"\x89PNG":
            return False, f"First frame is not valid PNG: {pngs[0]}"

    return True, f"Composited: {len(pngs)} frames in {output_dir}"
