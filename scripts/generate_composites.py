#!/usr/bin/env python3
"""Generate 9 fashion campaign composites using Gemini 2.5 Flash Image."""

import base64, requests, json, os, sys, time
from PIL import Image
from io import BytesIO

API_KEY = os.environ["GOOGLE_API_KEY"]
URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key={API_KEY}"

GARMENT = "/home/devuser/workspace/campaign/THG-world-record-attempt/assets/garment-panels/look6_front.jpg"
SCENE_GRID = "/home/devuser/workspace/campaign/THG-world-record-attempt/input-scenes/90CM-CheckWhite-2.jpg"
SCENE_NEON = "/home/devuser/workspace/campaign/THG-world-record-attempt/input-scenes/freepik__remove-the-deformed-mannequin-out-of-img1-and-add-__81164.png"
SCENE_TRON = "/home/devuser/workspace/campaign/THG-world-record-attempt/input-scenes/freepik__using-img1-as-the-locked-scene-replace-the-existin__31278.png"
OUT_DIR = "/home/devuser/workspace/campaign/THG-world-record-attempt/assets/scene-riffs/composited"


def load_and_resize(path, max_edge=1536):
    img = Image.open(path)
    w, h = img.size
    if max(w, h) > max_edge:
        scale = max_edge / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    buf = BytesIO()
    fmt = "JPEG" if path.lower().endswith(".jpg") else "PNG"
    img.save(buf, format=fmt, quality=92)
    return base64.b64encode(buf.getvalue()).decode(), "image/jpeg" if fmt == "JPEG" else "image/png"


def generate(garment_path, scene_path, prompt, output_path, seed=42, attempt=1):
    garment_b64, garment_mime = load_and_resize(garment_path, 1024)
    scene_b64, scene_mime = load_and_resize(scene_path, 1536)

    payload = {
        "contents": [{"parts": [
            {"inlineData": {"mimeType": garment_mime, "data": garment_b64}},
            {"inlineData": {"mimeType": scene_mime, "data": scene_b64}},
            {"text": prompt}
        ]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"], "seed": seed}
    }

    try:
        resp = requests.post(URL, json=payload, timeout=180)
        if resp.status_code == 429:
            wait = 30 * attempt
            print(f"  Rate limited, waiting {wait}s before retry...")
            time.sleep(wait)
            if attempt < 4:
                return generate(garment_path, scene_path, prompt, output_path, seed, attempt + 1)
            else:
                print(f"FAIL {os.path.basename(output_path)}: rate limited after {attempt} attempts")
                return False
        if resp.status_code != 200:
            print(f"FAIL {os.path.basename(output_path)}: HTTP {resp.status_code} - {resp.text[:200]}")
            if attempt < 3:
                time.sleep(15)
                return generate(garment_path, scene_path, prompt, output_path, seed, attempt + 1)
            return False

        data = resp.json()

        for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
            if "inlineData" in part:
                img_data = base64.b64decode(part["inlineData"]["data"])
                with open(output_path, "wb") as f:
                    f.write(img_data)
                size_kb = len(img_data) // 1024
                print(f"OK {os.path.basename(output_path)}: {size_kb}KB")
                return True

        # Check for text-only response
        text_parts = [p.get("text", "") for p in data.get("candidates", [{}])[0].get("content", {}).get("parts", []) if "text" in p]
        if text_parts:
            print(f"  Model returned text: {' '.join(text_parts)[:200]}")

        print(f"FAIL {os.path.basename(output_path)}: no image in response")
        if attempt < 3:
            time.sleep(10)
            return generate(garment_path, scene_path, prompt, output_path, seed + 1, attempt + 1)
        return False

    except requests.exceptions.Timeout:
        print(f"FAIL {os.path.basename(output_path)}: timeout")
        if attempt < 3:
            time.sleep(10)
            return generate(garment_path, scene_path, prompt, output_path, seed, attempt + 1)
        return False
    except Exception as e:
        print(f"FAIL {os.path.basename(output_path)}: {e}")
        return False


# Define all 9 composites
COMPOSITES = [
    # White Grid Room - 3 variations
    {
        "scene": SCENE_GRID,
        "output": "composite_grid_center.png",
        "seed": 42,
        "prompt": "I am giving you two images. IMAGE 1 is a reference garment: a cream sleeveless maxi dress with delicate black ink botanical illustrations (chrysanthemum flowers, birds) on the bodice and THIN VERTICAL PINSTRIPES on the flowing A-line skirt, with thin chain link straps. IMAGE 2 is a white tiled grid room with floating white smiley face balloons. Generate a single fashion campaign photograph: place ONE polished chrome mannequin wearing the EXACT dress from IMAGE 1 in the CENTER of the room from IMAGE 2. The mannequin should be walking confidently forward. Keep ALL floating smiley face balloons exactly as they are. Keep the white grid room environment. The dress must show: thin vertical pinstripes on skirt, botanical ink on bodice, chain straps, cream fabric. Professional fashion editorial, sharp focus. Output ONE image only."
    },
    {
        "scene": SCENE_GRID,
        "output": "composite_grid_walking.png",
        "seed": 123,
        "prompt": "Two images provided. IMAGE 1: reference garment - cream maxi dress with black ink chrysanthemum botanical art on bodice, thin vertical pinstripes on A-line skirt, chain link straps. IMAGE 2: surreal white tiled cube room with floating smiley face balloons. Create a dynamic fashion editorial: a sleek chrome mannequin in mid-stride wearing the EXACT dress from IMAGE 1, walking through the white grid room. One smiley balloon should be very close to camera (foreground blur), others floating in background. The dress flows with movement. CRITICAL: thin vertical pinstripes on skirt, botanical ink bodice, chain straps. Surreal pop-art fashion editorial. ONE image."
    },
    {
        "scene": SCENE_GRID,
        "output": "composite_grid_sitting.png",
        "seed": 456,
        "prompt": "Two images. IMAGE 1: cream sleeveless maxi with black ink botanical chrysanthemum bodice, thin vertical pinstripes on A-line skirt, chain straps. IMAGE 2: white tiled grid room with floating smiley face balloons. Generate: a chrome mannequin sitting gracefully on the tiled floor, legs extended, wearing the EXACT dress from IMAGE 1. The pinstriped skirt fans out beautifully on the white tiles. Smiley face balloons float overhead. Serene, editorial, high-fashion. THIN VERTICAL PINSTRIPES on skirt, botanical ink on bodice. ONE image only."
    },
    # Neon Corridor - 3 variations
    {
        "scene": SCENE_NEON,
        "output": "composite_neon_emerge.png",
        "seed": 789,
        "prompt": "Two images. IMAGE 1: cream sleeveless maxi dress with delicate black ink chrysanthemum and bird illustrations on bodice, THIN VERTICAL PINSTRIPES on flowing A-line skirt, thin chain link straps. IMAGE 2: dark moody corridor with vertical neon light bars in teal/blue. Generate: a polished chrome mannequin emerging from the darkness of IMAGE 2's corridor, wearing the EXACT dress from IMAGE 1. The neon lights create dramatic rim lighting on the chrome skin and illuminate the dress fabric. The cream dress glows against the dark environment. THIN VERTICAL PINSTRIPES on skirt. Cinematic, high-fashion editorial, moody. ONE image."
    },
    {
        "scene": SCENE_NEON,
        "output": "composite_neon_profile.png",
        "seed": 1024,
        "prompt": "Two images. IMAGE 1: reference garment - cream maxi with black ink botanical art (chrysanthemums, birds) on bodice, thin vertical pinstripes on A-line skirt, chain straps. IMAGE 2: dark futuristic corridor with vertical neon teal light bars. Create: a side-profile fashion shot of a chrome mannequin wearing the EXACT dress from IMAGE 1, standing in IMAGE 2's neon corridor. The mannequin faces right. Neon light catches the chrome reflections and illuminates the cream fabric. The thin vertical pinstripes on the skirt are visible in the neon glow. Editorial, atmospheric. ONE image."
    },
    {
        "scene": SCENE_NEON,
        "output": "composite_neon_dramatic.png",
        "seed": 2048,
        "prompt": "Two images. IMAGE 1: cream sleeveless maxi - black ink chrysanthemum botanical art on bodice, THIN VERTICAL PINSTRIPES on A-line skirt, chain link straps. IMAGE 2: dark corridor with vertical neon light bars. Generate: dramatic LOW ANGLE fashion shot looking UP at a chrome mannequin wearing the EXACT dress from IMAGE 1, standing powerful in IMAGE 2's neon corridor. The vertical neon bars frame the mannequin like cathedral pillars. The dress cascades down, pinstripes visible. Powerful, editorial, cinematic. ONE image."
    },
    # Black Grid Room - 3 variations
    {
        "scene": SCENE_TRON,
        "output": "composite_tron_standing.png",
        "seed": 3333,
        "prompt": "Two images. IMAGE 1: cream sleeveless maxi dress with black ink botanical chrysanthemum illustrations on bodice, THIN VERTICAL PINSTRIPES on A-line skirt, thin chain link straps. IMAGE 2: black room with luminous blue/white neon grid lines on floor, walls, and ceiling - like Tron. Generate: a single polished chrome mannequin standing center-frame in IMAGE 2's black grid room, wearing the EXACT dress from IMAGE 1. The neon grid lines reflect off the chrome body. The cream dress contrasts dramatically against the dark environment. THIN VERTICAL PINSTRIPES on skirt. Futuristic editorial. ONE image."
    },
    {
        "scene": SCENE_TRON,
        "output": "composite_tron_seated.png",
        "seed": 4444,
        "prompt": "Two images. IMAGE 1: cream maxi dress - botanical ink chrysanthemums on bodice, thin vertical pinstripes on A-line skirt, chain link straps. IMAGE 2: black Tron-like grid room with neon lines and geometric cube structures. Create: a chrome mannequin sitting on one of the geometric cube structures in IMAGE 2's grid room, wearing the EXACT dress from IMAGE 1. The pinstriped skirt drapes over the edge. Neon grid lines glow around the scene. Avant-garde, futuristic fashion editorial. THIN VERTICAL PINSTRIPES on skirt. ONE image."
    },
    {
        "scene": SCENE_TRON,
        "output": "composite_tron_duo.png",
        "seed": 5555,
        "prompt": "Two images. IMAGE 1: cream sleeveless maxi - black ink chrysanthemum botanical art on bodice, THIN VERTICAL PINSTRIPES on A-line skirt, chain link straps. IMAGE 2: black grid room with neon blue lines everywhere, geometric structures. Generate: TWO chrome mannequins BOTH wearing the EXACT same dress from IMAGE 1, posed in IMAGE 2's black grid room. One standing, one seated on the geometric structure. Both dresses must show thin vertical pinstripes on skirts and botanical ink on bodices. Twin fashion editorial, surreal. ONE image."
    },
]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    success_count = 0
    total = len(COMPOSITES)

    print(f"Generating {total} composites...")
    print(f"Output: {OUT_DIR}")
    print("=" * 60)

    for i, comp in enumerate(COMPOSITES, 1):
        output_path = os.path.join(OUT_DIR, comp["output"])
        print(f"\n[{i}/{total}] {comp['output']} (seed={comp['seed']})")
        ok = generate(GARMENT, comp["scene"], comp["prompt"], output_path, comp["seed"])
        if ok:
            success_count += 1
        # Rate limit courtesy pause between requests
        if i < total:
            time.sleep(5)

    print("\n" + "=" * 60)
    print("File sizes:")
    for comp in COMPOSITES:
        fpath = os.path.join(OUT_DIR, comp["output"])
        if os.path.exists(fpath):
            size_kb = os.path.getsize(fpath) // 1024
            print(f"  {comp['output']}: {size_kb}KB")
        else:
            print(f"  {comp['output']}: MISSING")

    print(f"\nCOMPOSITES DONE: {success_count}/{total} successful")


if __name__ == "__main__":
    main()
