#!/usr/bin/env python3
"""Batch 1 Repose Agent: Images 1-10
Reposes chrome mannequin fashion images to match reference poses 24 and 26
using Nano Banana (gemini-2.5-flash-image).
"""

import base64, requests, json, os, time, sys
from PIL import Image
from io import BytesIO

API_KEY = os.environ["GOOGLE_API_KEY"]
URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key={API_KEY}"

SRC_DIR = "/home/devuser/workspace/campaign/THG-world-record-attempt/task-two-repose/Posed Mannequins 4/Posed Mannequins"
OUT_DIR = "/home/devuser/workspace/campaign/THG-world-record-attempt/task-two-repose/output-reposed"

os.makedirs(OUT_DIR, exist_ok=True)


def load_b64(path, max_edge=2048):
    """Load image, resize for API, return b64 string."""
    img = Image.open(path).convert("RGB")
    w, h = img.size
    if max(w, h) > max_edge:
        scale = max_edge / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return base64.b64encode(buf.getvalue()).decode()


def repose(source_path, pose_ref_path, pose_desc, output_name, seed=42):
    """Repose a mannequin image to match a reference pose."""
    print(f"\n--- Processing {os.path.basename(source_path)} -> {output_name} ---")
    sys.stdout.flush()

    if not os.path.exists(source_path):
        print(f"FAIL {output_name}: source not found: {source_path}")
        return False
    if not os.path.exists(pose_ref_path):
        print(f"FAIL {output_name}: pose ref not found: {pose_ref_path}")
        return False

    source_b64 = load_b64(source_path, 1536)
    pose_b64 = load_b64(pose_ref_path, 1536)

    prompt = f"""I am giving you two images:

IMAGE 1 (source): A chrome mannequin in a concrete studio wearing a specific outfit. This is the image to transform.

IMAGE 2 (pose reference): A chrome mannequin in a different pose. This is the TARGET POSE to replicate.

YOUR TASK: Generate a single image that takes the EXACT mannequin and EXACT outfit/clothes/accessories/shoes from IMAGE 1, but changes the body pose to EXACTLY match the stance and body position from IMAGE 2.

CRITICAL REQUIREMENTS:
1. The OUTFIT must be IDENTICAL to IMAGE 1 - same clothes, same colors, same accessories, same shoes, same bag
2. The BODY POSE must match IMAGE 2 - {pose_desc}
3. The STUDIO ENVIRONMENT must remain the same concrete room with softbox lighting
4. The chrome mannequin skin/head must remain the same
5. Output at high resolution, maintain the 3:4 portrait aspect ratio

Do NOT change the outfit. Do NOT change the environment. ONLY change the body pose to match IMAGE 2.
Output ONE image only."""

    payload = {
        "contents": [{"parts": [
            {"inlineData": {"mimeType": "image/jpeg", "data": source_b64}},
            {"inlineData": {"mimeType": "image/jpeg", "data": pose_b64}},
            {"text": prompt}
        ]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}
    }

    try:
        resp = requests.post(URL, json=payload, timeout=180)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.Timeout:
        print(f"FAIL {output_name}: request timed out (180s)")
        return False
    except requests.exceptions.RequestException as e:
        print(f"FAIL {output_name}: request error: {e}")
        return False
    except json.JSONDecodeError:
        print(f"FAIL {output_name}: invalid JSON response")
        return False

    # Check for API-level errors
    if "error" in data:
        err_msg = data["error"].get("message", "unknown error")
        print(f"FAIL {output_name}: API error: {err_msg[:300]}")
        return False

    # Extract generated image from response
    candidates = data.get("candidates", [])
    if not candidates:
        print(f"FAIL {output_name}: no candidates in response")
        # Print any useful debug info
        if "promptFeedback" in data:
            print(f"  promptFeedback: {json.dumps(data['promptFeedback'])[:300]}")
        return False

    parts = candidates[0].get("content", {}).get("parts", [])
    for part in parts:
        if "inlineData" in part:
            img_data = base64.b64decode(part["inlineData"]["data"])
            outpath = os.path.join(OUT_DIR, output_name)
            with open(outpath, "wb") as f:
                f.write(img_data)
            # Verify and report
            img = Image.open(outpath)
            size_kb = len(img_data) // 1024
            print(f"OK {output_name}: {size_kb}KB, {img.size[0]}x{img.size[1]}")
            sys.stdout.flush()
            return True

    # No image found in parts - print text parts for debugging
    text_parts = [p.get("text", "") for p in parts if "text" in p]
    if text_parts:
        print(f"FAIL {output_name}: no image in response. Text: {' '.join(text_parts)[:300]}")
    else:
        print(f"FAIL {output_name}: no image data in response parts")
    return False


# Reference pose paths
POSE_24 = os.path.join(SRC_DIR, "24-Reference for pose.png")
POSE_26 = os.path.join(SRC_DIR, "26-Reference for pose.png")

POSE_24_DESC = "feet apart, right hand holding bag at side, shoulders back, strong confident editorial power pose, facing forward"
POSE_26_DESC = "walking stride, crossed legs mid-step, holding bag in left hand, weight shifted forward, dynamic movement, slight turn"

# Images 1-10 alternating between pose 24 and 26
assignments = [
    ("1.png",  POSE_24, POSE_24_DESC, "reposed_01_pose24.png", 100),
    ("2.png",  POSE_26, POSE_26_DESC, "reposed_02_pose26.png", 200),
    ("3.png",  POSE_24, POSE_24_DESC, "reposed_03_pose24.png", 300),
    ("4.png",  POSE_26, POSE_26_DESC, "reposed_04_pose26.png", 400),
    ("5.png",  POSE_24, POSE_24_DESC, "reposed_05_pose24.png", 500),
    ("6.png",  POSE_26, POSE_26_DESC, "reposed_06_pose26.png", 600),
    ("7.png",  POSE_24, POSE_24_DESC, "reposed_07_pose24.png", 700),
    ("8.png",  POSE_26, POSE_26_DESC, "reposed_08_pose26.png", 800),
    ("9.png",  POSE_24, POSE_24_DESC, "reposed_09_pose24.png", 900),
    ("10.png", POSE_26, POSE_26_DESC, "reposed_10_pose26.png", 1000),
]

print("=" * 60)
print("BATCH 1 REPOSE AGENT: Images 1-10")
print(f"Source: {SRC_DIR}")
print(f"Output: {OUT_DIR}")
print(f"Pose 24 ref: {os.path.exists(POSE_24)}")
print(f"Pose 26 ref: {os.path.exists(POSE_26)}")
print("=" * 60)
sys.stdout.flush()

success = 0
failures = []
start_time = time.time()

for idx, (src_name, pose_path, pose_desc, out_name, seed) in enumerate(assignments):
    src_path = os.path.join(SRC_DIR, src_name)
    attempt_start = time.time()

    if repose(src_path, pose_path, pose_desc, out_name, seed):
        success += 1
    else:
        failures.append(src_name)

    elapsed = time.time() - attempt_start
    print(f"  Time: {elapsed:.1f}s | Progress: {idx + 1}/10 | Success: {success}")
    sys.stdout.flush()

    # Rate limiting between requests
    if idx < len(assignments) - 1:
        time.sleep(2)

total_time = time.time() - start_time

print("\n" + "=" * 60)
print(f"BATCH 1 COMPLETE: {success}/10 successful")
print(f"Total time: {total_time:.1f}s")
if failures:
    print(f"Failed images: {', '.join(failures)}")
print("=" * 60)

# List output files
print("\nOutput files:")
for f in sorted(os.listdir(OUT_DIR)):
    if f.startswith("reposed_") and f.endswith(".png"):
        fpath = os.path.join(OUT_DIR, f)
        size_kb = os.path.getsize(fpath) // 1024
        img = Image.open(fpath)
        print(f"  {f}: {size_kb}KB, {img.size[0]}x{img.size[1]}")
