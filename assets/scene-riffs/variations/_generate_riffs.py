#!/usr/bin/env python3
"""Creative Riff Generator - 10 high-concept fashion editorial images."""

import base64, requests, json, os, sys, time
from PIL import Image
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed

API_KEY = os.environ["GOOGLE_API_KEY"]
GARMENT = "/home/devuser/workspace/campaign/THG-world-record-attempt/assets/garment-panels/look6_front.jpg"
OUTDIR = "/home/devuser/workspace/campaign/THG-world-record-attempt/assets/scene-riffs/variations"

def load_b64(path, max_edge=1024):
    img = Image.open(path)
    w, h = img.size
    if max(w, h) > max_edge:
        scale = max_edge / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    buf = BytesIO()
    fmt = "JPEG" if path.lower().endswith(".jpg") else "PNG"
    img.save(buf, format=fmt, quality=92)
    return base64.b64encode(buf.getvalue()).decode(), "image/jpeg" if fmt == "JPEG" else "image/png"

def try_pro_then_flash(garment_b64, garment_mime, prompt, output_path, attempt=1):
    """Try Flash Preview first, fall back to Flash stable."""
    models = [
        "gemini-2.5-flash-preview-image-generation",
        "gemini-2.5-flash-image"
    ]
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}"
        payload = {
            "contents": [{"parts": [
                {"inlineData": {"mimeType": garment_mime, "data": garment_b64}},
                {"text": prompt}
            ]}],
            "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}
        }
        try:
            resp = requests.post(url, json=payload, timeout=180)
            if resp.status_code == 429:
                print(f"  RATE-LIMITED [{model}] for {os.path.basename(output_path)}, waiting 15s...", flush=True)
                time.sleep(15)
                resp = requests.post(url, json=payload, timeout=180)
            if resp.status_code == 503 or resp.status_code == 500:
                print(f"  SERVER ERROR {resp.status_code} [{model}] for {os.path.basename(output_path)}", flush=True)
                continue
            data = resp.json()
            # Check for error in response
            if "error" in data:
                emsg = data["error"].get("message", "unknown")
                print(f"  API ERROR [{model}] {os.path.basename(output_path)}: {emsg[:100]}", flush=True)
                continue
            candidates = data.get("candidates", [{}])
            if not candidates:
                print(f"  NO CANDIDATES [{model}] {os.path.basename(output_path)}", flush=True)
                continue
            parts = candidates[0].get("content", {}).get("parts", [])
            for part in parts:
                if "inlineData" in part:
                    img_data = base64.b64decode(part["inlineData"]["data"])
                    with open(output_path, "wb") as f:
                        f.write(img_data)
                    kb = len(img_data) // 1024
                    print(f"  OK [{model}] {os.path.basename(output_path)}: {kb}KB", flush=True)
                    return True
            # No image in parts
            text_parts = [p.get("text", "") for p in parts if "text" in p]
            if text_parts:
                print(f"  TEXT-ONLY [{model}] {os.path.basename(output_path)}: {text_parts[0][:120]}", flush=True)
            else:
                print(f"  NO-IMAGE [{model}] {os.path.basename(output_path)}", flush=True)
        except requests.exceptions.Timeout:
            print(f"  TIMEOUT [{model}] {os.path.basename(output_path)}", flush=True)
            continue
        except Exception as e:
            print(f"  WARN [{model}] {os.path.basename(output_path)}: {e}", flush=True)
            continue
    print(f"  FAIL {os.path.basename(output_path)} (all models)", flush=True)
    return False

# Define all 10 riffs
RIFFS = [
    # --- Smiley Theme Riffs ---
    ("riff_smiley_rain.png",
     "A chrome mannequin wearing the dress from IMAGE 1 standing in heavy rain on a dark street. Giant 3-meter white smiley face balloons float in the sky above like weather balloons. Rain streaks past. The cream dress with thin vertical pinstripes and botanical ink bodice is soaked and clinging dramatically. Cinematic fashion editorial, moody weather. ONE image."),

    ("riff_smiley_field.png",
     "A polished chrome mannequin wearing the EXACT dress from IMAGE 1 (cream maxi with thin vertical pinstripes on skirt, black ink chrysanthemum botanical art on bodice, chain link straps) standing alone in an infinite white void. Dozens of white smiley face spheres float at various distances, some huge, some tiny. Minimalist surreal fashion art. Clean, eerie, beautiful. ONE image."),

    ("riff_smiley_underwater.png",
     "Surreal underwater fashion editorial. A chrome mannequin wearing the dress from IMAGE 1 (cream maxi, thin vertical pinstripes, botanical ink bodice, chain straps) appears to float underwater in crystal-clear turquoise water. White smiley face balloons drift past like jellyfish. Light rays filter from above. The dress flows ethereally in the water. Dreamy, surreal. ONE image."),

    # --- Neon Theme Riffs ---
    ("riff_neon_cityscape.png",
     "Night-time fashion editorial on a Tokyo rooftop. A chrome mannequin wearing the dress from IMAGE 1 (cream sleeveless maxi, thin vertical pinstripes on A-line skirt, black ink chrysanthemum bodice, chain straps) stands on a rain-slicked rooftop. Neon signs and city lights blur in the background. The cream dress almost glows against the dark cityscape. Blade Runner meets haute couture. ONE image."),

    ("riff_neon_laser.png",
     "A chrome mannequin wearing the EXACT dress from IMAGE 1 (thin vertical pinstripes, botanical ink chrysanthemums, chain straps, cream maxi) standing in a dark void. Geometric laser beams in electric blue and magenta slice through the darkness around the mannequin but don't touch it. The dress catches light from the lasers. Dramatic, sci-fi editorial. ONE image."),

    # --- Tron/Grid Theme Riffs ---
    ("riff_grid_infinity.png",
     "A chrome mannequin wearing the dress from IMAGE 1 (cream maxi with thin vertical pinstripes, botanical ink bodice, chain link straps) standing in an infinite mirror room. The mannequin and dress reflect infinitely in all directions. Moody blue-white lighting. The thin vertical pinstripes create mesmerizing patterns in the reflections. Yayoi Kusama meets fashion editorial. ONE image."),

    ("riff_grid_hologram.png",
     "Fashion editorial concept: a chrome mannequin wearing the dress from IMAGE 1 (cream sleeveless maxi, thin vertical pinstripes on skirt, black ink chrysanthemum botanical bodice, chain straps) appears as a HOLOGRAPHIC PROJECTION in a dark tech space. Scan lines and digital artifacts partially distort the image. Glowing blue grid on the floor. The dress is the only warm-toned element. Cyberpunk editorial. ONE image."),

    # --- Wildcard Riffs ---
    ("riff_museum.png",
     "A chrome mannequin wearing the dress from IMAGE 1 (cream maxi, thin vertical pinstripes, botanical ink chrysanthemum bodice, chain straps) displayed as an art installation in a grand white marble museum gallery. Velvet rope around it. Other visitors are blurred in the background. One white smiley face balloon floats near the ceiling. Art meets fashion. Shot on medium format. ONE image."),

    ("riff_desert.png",
     "Golden hour fashion editorial in a vast empty desert. A lone chrome mannequin wearing the dress from IMAGE 1 (cream sleeveless maxi with thin vertical pinstripes on the flowing skirt, delicate black ink chrysanthemum botanical art on bodice, thin chain link straps) stands on cracked earth. Wind blows the skirt. Two white smiley face balloons float in the amber sky. The warm light makes the cream dress glow. Surreal, desolate, beautiful. ONE image."),

    ("riff_greenhouse.png",
     "A chrome mannequin wearing the dress from IMAGE 1 (cream maxi, thin vertical pinstripes, botanical ink chrysanthemum bodice, chain straps) inside a lush Victorian greenhouse filled with real chrysanthemum flowers. The botanical illustrations on the bodice mirror the real flowers around it. Dappled sunlight through glass. Nature meets artifice. High-fashion editorial. ONE image."),
]

def generate_one(args):
    """Generate a single riff image."""
    idx, filename, prompt, garment_b64, garment_mime = args
    output_path = os.path.join(OUTDIR, filename)
    print(f"[{idx+1}/10] Generating {filename}...", flush=True)
    ok = try_pro_then_flash(garment_b64, garment_mime, prompt, output_path)
    return filename, ok

def main():
    print("=" * 60)
    print("CREATIVE RIFF GENERATOR - 10 High-Concept Fashion Images")
    print("=" * 60)

    # Load garment once
    print(f"\nLoading garment: {GARMENT}")
    garment_b64, garment_mime = load_b64(GARMENT)
    print(f"Garment loaded: {len(garment_b64) // 1024}KB base64\n")

    # Generate sequentially with small delays to avoid rate limits
    # (parallel would be faster but risks 429s heavily)
    results = {}
    success = 0
    fail = 0

    for idx, (filename, prompt) in enumerate(RIFFS):
        output_path = os.path.join(OUTDIR, filename)
        print(f"[{idx+1}/10] Generating {filename}...", flush=True)
        ok = try_pro_then_flash(garment_b64, garment_mime, prompt, output_path)
        results[filename] = ok
        if ok:
            success += 1
        else:
            fail += 1
        # Small delay between requests to be kind to the API
        if idx < len(RIFFS) - 1:
            time.sleep(2)

    # Retry failures once
    failures = [fn for fn, ok in results.items() if not ok]
    if failures:
        print(f"\n--- Retrying {len(failures)} failures after 10s cooldown ---", flush=True)
        time.sleep(10)
        for fn in failures:
            prompt = next(p for f, p in RIFFS if f == fn)
            output_path = os.path.join(OUTDIR, fn)
            print(f"  RETRY {fn}...", flush=True)
            ok = try_pro_then_flash(garment_b64, garment_mime, prompt, output_path)
            if ok:
                results[fn] = True
                success += 1
                fail -= 1
            time.sleep(3)

    # Summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    for fn, ok in results.items():
        status = "OK" if ok else "FAIL"
        size = ""
        path = os.path.join(OUTDIR, fn)
        if ok and os.path.exists(path):
            size = f" ({os.path.getsize(path) // 1024}KB)"
        print(f"  [{status}] {fn}{size}")

    total_ok = sum(1 for v in results.values() if v)
    print(f"\nRIFFS DONE: {total_ok}/10 successful")

if __name__ == "__main__":
    main()
