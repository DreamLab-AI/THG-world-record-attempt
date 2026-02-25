import base64, requests, json, os, time
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
        img = img.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return base64.b64encode(buf.getvalue()).decode()

def repose(source_path, pose_ref_path, pose_desc, output_name):
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
    resp = requests.post(URL, json=payload, timeout=180)
    data = resp.json()
    for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
        if "inlineData" in part:
            img_data = base64.b64decode(part["inlineData"]["data"])
            with open(os.path.join(OUT_DIR, output_name), "wb") as f:
                f.write(img_data)
            img = Image.open(os.path.join(OUT_DIR, output_name))
            print(f"OK {output_name}: {len(img_data)//1024}KB, {img.size}")
            return True
    print(f"FAIL {output_name}")
    if "error" in data:
        print(f"  Error: {data['error'].get('message', 'unknown')}")
    return False

POSE_24 = os.path.join(SRC_DIR, "24-Reference for pose.png")
POSE_26 = os.path.join(SRC_DIR, "26-Reference for pose.png")
P24_DESC = "feet apart, right hand holding bag, shoulders back, strong confident editorial stance"
P26_DESC = "walking stride, crossed legs, holding bag in left hand, dynamic forward movement"

assignments = [
    ("25.png", POSE_24, P24_DESC, "reposed_25_pose24.png"),
    ("27.png", POSE_26, P26_DESC, "reposed_27_pose26.png"),
    ("28.png", POSE_24, P24_DESC, "reposed_28_pose24.png"),
    ("29.png", POSE_26, P26_DESC, "reposed_29_pose26.png"),
    ("30.png", POSE_24, P24_DESC, "reposed_30_pose24.png"),
]

print(f"BATCH 3 REPOSE: {len(assignments)} images")
print(f"Source dir: {SRC_DIR}")
print(f"Output dir: {OUT_DIR}")
print()

success = 0
for i, (src_name, pose_path, pose_desc, out_name) in enumerate(assignments, 1):
    src_path = os.path.join(SRC_DIR, src_name)
    print(f"[{i}/5] {src_name} -> {out_name}")
    if repose(src_path, pose_path, pose_desc, out_name):
        success += 1
    if i < len(assignments):
        time.sleep(2)

print(f"\nBATCH 3 DONE: {success}/5")
