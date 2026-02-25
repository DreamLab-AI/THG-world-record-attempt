import base64, requests, json, os, time, sys
from PIL import Image
from io import BytesIO

API_KEY = os.environ["GOOGLE_API_KEY"]
URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key={API_KEY}"
SRC_DIR = "/home/devuser/workspace/campaign/THG-world-record-attempt/task-two-repose/Posed Mannequins 4/Posed Mannequins"
OUT_DIR = "/home/devuser/workspace/campaign/THG-world-record-attempt/task-two-repose/output-reposed"

def load_b64(path, max_edge=1536):
    img = Image.open(path).convert("RGB")
    w, h = img.size
    if max(w, h) > max_edge:
        scale = max_edge / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return base64.b64encode(buf.getvalue()).decode()

def repose(source_path, pose_ref_path, pose_desc, output_name):
    print(f"Processing {output_name}...", flush=True)
    source_b64 = load_b64(source_path)
    pose_b64 = load_b64(pose_ref_path)
    prompt = f"""Two images provided.
IMAGE 1 (source): Chrome mannequin in concrete studio wearing a specific outfit.
IMAGE 2 (pose reference): Chrome mannequin in target body pose.

Generate ONE image: take the EXACT mannequin and EXACT outfit/clothes/accessories/shoes from IMAGE 1, change ONLY the body pose to match IMAGE 2's stance ({pose_desc}).

CRITICAL: Keep identical outfit from IMAGE 1. Keep concrete studio. Keep chrome mannequin. ONLY change pose to match IMAGE 2. 3:4 portrait. ONE image."""

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
        data = resp.json()

        if "error" in data:
            print(f"  API ERROR {output_name}: {data['error'].get('message', 'unknown')}", flush=True)
            return False

        for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
            if "inlineData" in part:
                img_data = base64.b64decode(part["inlineData"]["data"])
                out_path = os.path.join(OUT_DIR, output_name)
                with open(out_path, "wb") as f:
                    f.write(img_data)
                img = Image.open(out_path)
                print(f"  OK {output_name}: {len(img_data)//1024}KB, {img.size}", flush=True)
                return True

        # Check for text-only response (no image generated)
        for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
            if "text" in part:
                print(f"  TEXT ONLY {output_name}: {part['text'][:200]}", flush=True)

        print(f"  FAIL {output_name}: No image in response", flush=True)
        return False

    except Exception as e:
        print(f"  ERROR {output_name}: {e}", flush=True)
        return False

POSE_24 = os.path.join(SRC_DIR, "24-Reference for pose.png")
POSE_26 = os.path.join(SRC_DIR, "26-Reference for pose.png")
P24_DESC = "feet apart, right hand holding bag, shoulders back, strong confident editorial stance"
P26_DESC = "walking stride, crossed legs, holding bag in left hand, dynamic forward movement"

# Images 11-23 (skip 24 which is reference)
assignments = [
    ("11.png", POSE_26, P26_DESC, "reposed_11_pose26.png"),
    ("12.png", POSE_24, P24_DESC, "reposed_12_pose24.png"),
    ("13.png", POSE_26, P26_DESC, "reposed_13_pose26.png"),
    ("14.png", POSE_24, P24_DESC, "reposed_14_pose24.png"),
    ("15.png", POSE_26, P26_DESC, "reposed_15_pose26.png"),
    ("16.png", POSE_24, P24_DESC, "reposed_16_pose24.png"),
    ("17.png", POSE_26, P26_DESC, "reposed_17_pose26.png"),
    ("18.png", POSE_24, P24_DESC, "reposed_18_pose24.png"),
    ("19.png", POSE_26, P26_DESC, "reposed_19_pose26.png"),
    ("20.png", POSE_24, P24_DESC, "reposed_20_pose24.png"),
    ("21.png", POSE_26, P26_DESC, "reposed_21_pose26.png"),
    ("22.png", POSE_24, P24_DESC, "reposed_22_pose24.png"),
    ("23.png", POSE_26, P26_DESC, "reposed_23_pose26.png"),
]

print(f"BATCH 2: Reposing images 11-23 (13 images)", flush=True)
print(f"Source: {SRC_DIR}", flush=True)
print(f"Output: {OUT_DIR}", flush=True)
print(f"Pose refs: 24 (editorial stance) and 26 (walking stride)", flush=True)
print("=" * 60, flush=True)

success = 0
failed = []
for i, (src_name, pose_path, pose_desc, out_name) in enumerate(assignments, 1):
    src_path = os.path.join(SRC_DIR, src_name)
    if not os.path.exists(src_path):
        print(f"  SKIP {src_name}: file not found", flush=True)
        failed.append(out_name)
        continue
    print(f"\n[{i}/13] ", end="", flush=True)
    if repose(src_path, pose_path, pose_desc, out_name):
        success += 1
    else:
        failed.append(out_name)
    if i < len(assignments):
        time.sleep(2)

print("\n" + "=" * 60)
print(f"BATCH 2 DONE: {success}/13 successful")
if failed:
    print(f"Failed: {', '.join(failed)}")
