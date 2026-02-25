#!/usr/bin/env python3
"""
Scene Cleaner: Remove mannequins/subjects from scene images using Gemini 2.5 Flash.
Keeps balloons, environment, lighting, and atmosphere intact.
"""

import base64
import json
import os
import sys
import time
import requests
from io import BytesIO

try:
    from PIL import Image
except ImportError:
    print("Installing Pillow...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow", "-q"])
    from PIL import Image

API_KEY = os.environ["GOOGLE_API_KEY"]
URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key={API_KEY}"

INPUT_DIR = "/home/devuser/workspace/campaign/THG-world-record-attempt/input-scenes"
OUTPUT_DIR = "/home/devuser/workspace/campaign/THG-world-record-attempt/assets/scene-riffs/cleaned"

MAX_LONG_EDGE = 2048


def resize_if_needed(image_path, max_edge=MAX_LONG_EDGE):
    """Resize image if longest edge exceeds max_edge. Returns base64 and mime type."""
    img = Image.open(image_path)
    orig_size = img.size
    w, h = img.size

    needs_resize = max(w, h) > max_edge
    if needs_resize:
        if w > h:
            new_w = max_edge
            new_h = int(h * (max_edge / w))
        else:
            new_h = max_edge
            new_w = int(w * (max_edge / h))
        img = img.resize((new_w, new_h), Image.LANCZOS)
        print(f"  Resized from {orig_size} to {img.size}")
    else:
        print(f"  Image size: {orig_size} (no resize needed)")

    # Convert RGBA to RGB for JPEG-compatible output
    if img.mode == "RGBA":
        # Keep as PNG
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return base64.b64encode(buf.read()).decode(), "image/png"
    else:
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=95)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode(), "image/jpeg"


def clean_scene(image_path, prompt, output_path, max_retries=3):
    """Send image to Gemini API with cleaning prompt and save result."""
    print(f"\nProcessing: {os.path.basename(image_path)}")
    print(f"  Output: {os.path.basename(output_path)}")

    img_b64, mime = resize_if_needed(image_path)
    print(f"  Base64 size: {len(img_b64) // 1024} KB, MIME: {mime}")

    payload = {
        "contents": [{"parts": [
            {"inlineData": {"mimeType": mime, "data": img_b64}},
            {"text": prompt}
        ]}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"]
        }
    }

    for attempt in range(1, max_retries + 1):
        print(f"  Sending to Gemini API (attempt {attempt}/{max_retries})...")
        try:
            resp = requests.post(URL, json=payload, timeout=180)

            if resp.status_code == 429:
                wait = 30 * attempt
                print(f"  Rate limited (429). Waiting {wait}s...")
                time.sleep(wait)
                continue

            if resp.status_code != 200:
                print(f"  API error {resp.status_code}: {resp.text[:500]}")
                if attempt < max_retries:
                    time.sleep(10 * attempt)
                    continue
                return False

            data = resp.json()

            # Check for errors in response
            if "error" in data:
                print(f"  API error: {data['error'].get('message', str(data['error']))}")
                if attempt < max_retries:
                    time.sleep(10 * attempt)
                    continue
                return False

            # Extract image from response
            candidates = data.get("candidates", [])
            if not candidates:
                print(f"  No candidates in response")
                print(f"  Response keys: {list(data.keys())}")
                if attempt < max_retries:
                    time.sleep(10)
                    continue
                return False

            parts = candidates[0].get("content", {}).get("parts", [])

            image_found = False
            text_response = ""
            for part in parts:
                if "text" in part:
                    text_response = part["text"]
                if "inlineData" in part:
                    img_data = base64.b64decode(part["inlineData"]["data"])
                    with open(output_path, "wb") as f:
                        f.write(img_data)
                    file_size = os.path.getsize(output_path)
                    print(f"  Saved: {output_path} ({file_size / 1024:.1f} KB)")
                    image_found = True
                    break

            if text_response:
                print(f"  Model text: {text_response[:200]}")

            if not image_found:
                print(f"  No image in response parts. Part types: {[list(p.keys()) for p in parts]}")
                if attempt < max_retries:
                    time.sleep(10)
                    continue
                return False

            return True

        except requests.exceptions.Timeout:
            print(f"  Timeout on attempt {attempt}")
            if attempt < max_retries:
                time.sleep(15)
                continue
            return False
        except Exception as e:
            print(f"  Error: {e}")
            if attempt < max_retries:
                time.sleep(10)
                continue
            return False

    return False


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    scenes = [
        {
            "input": os.path.join(INPUT_DIR, "90CM-CheckWhite-2.jpg"),
            "output": os.path.join(OUTPUT_DIR, "cleaned_white_grid.png"),
            "prompt": (
                "Remove BOTH mannequin figures from this image. "
                "Keep the white tiled grid room EXACTLY as it is. "
                "Keep ALL floating white smiley face balloons exactly where they are - do NOT remove them. "
                "Keep the floor, walls, ceiling, lighting all intact. "
                "The result should be an empty white grid room with floating smiley face balloons and nothing else. "
                "Output ONE image."
            )
        },
        {
            "input": os.path.join(INPUT_DIR, "freepik__remove-the-deformed-mannequin-out-of-img1-and-add-__81164.png"),
            "output": os.path.join(OUTPUT_DIR, "cleaned_neon_corridor.png"),
            "prompt": (
                "Remove the robot/mannequin figure from the center of this image. "
                "Keep the dark corridor with vertical neon light bars EXACTLY as it is. "
                "Keep the moody dark blue/teal lighting, the reflective floor, all neon elements. "
                "The result should be an empty dark neon corridor with no figure in it. "
                "Output ONE image."
            )
        },
        {
            "input": os.path.join(INPUT_DIR, "freepik__using-img1-as-the-locked-scene-replace-the-existin__31278.png"),
            "output": os.path.join(OUTPUT_DIR, "cleaned_black_grid.png"),
            "prompt": (
                "Remove BOTH mannequin figures from this image. "
                "Keep the black grid room with neon blue grid lines EXACTLY as it is. "
                "Keep the overhead fluorescent lights, the geometric cube/shelf structures, the reflective floor. "
                "The result should be an empty black grid room with neon lines and no figures. "
                "Output ONE image."
            )
        }
    ]

    results = {}
    for scene in scenes:
        name = os.path.basename(scene["output"])
        success = clean_scene(scene["input"], scene["prompt"], scene["output"])
        results[name] = success
        # Pause between API calls to avoid rate limiting
        if scene != scenes[-1]:
            print("  Waiting 5s before next scene...")
            time.sleep(5)

    # Print summary
    print("\n" + "=" * 60)
    print("SCENE CLEANING SUMMARY")
    print("=" * 60)

    for name, success in results.items():
        output_path = os.path.join(OUTPUT_DIR, name)
        if success and os.path.exists(output_path):
            size = os.path.getsize(output_path)
            print(f"  {name}: OK ({size / 1024:.1f} KB)")
        else:
            print(f"  {name}: FAILED")

    # List all output files
    print(f"\nOutput directory: {OUTPUT_DIR}")
    if os.path.exists(OUTPUT_DIR):
        for f in sorted(os.listdir(OUTPUT_DIR)):
            fp = os.path.join(OUTPUT_DIR, f)
            if os.path.isfile(fp):
                print(f"  {f}: {os.path.getsize(fp) / 1024:.1f} KB")


if __name__ == "__main__":
    main()
