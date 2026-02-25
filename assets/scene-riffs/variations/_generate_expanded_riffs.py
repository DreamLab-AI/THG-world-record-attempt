#!/usr/bin/env python3
"""Generate 15 expanded creative riff variations of the Topshop dress."""

import base64, requests, json, os, time, sys
from PIL import Image
from io import BytesIO

API_KEY = os.environ["GOOGLE_API_KEY"]
GARMENT = "/home/devuser/workspace/campaign/THG-world-record-attempt/assets/garment-panels/look6_front.jpg"
OUT_DIR = "/home/devuser/workspace/campaign/THG-world-record-attempt/assets/scene-riffs/variations"

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

def generate(garment_path, prompt, output_path, attempt=1):
    garment_b64, garment_mime = load_b64(garment_path)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key={API_KEY}"
    payload = {
        "contents": [{"parts": [
            {"inlineData": {"mimeType": garment_mime, "data": garment_b64}},
            {"text": prompt}
        ]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}
    }
    try:
        resp = requests.post(url, json=payload, timeout=120)
        data = resp.json()
        for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
            if "inlineData" in part:
                img_data = base64.b64decode(part["inlineData"]["data"])
                with open(output_path, "wb") as f:
                    f.write(img_data)
                print(f"  OK {os.path.basename(output_path)}: {len(img_data)//1024}KB", flush=True)
                return True
        err_info = json.dumps(data.get("error", data.get("candidates", [])), indent=2)[:300]
        print(f"  FAIL {os.path.basename(output_path)}: {err_info}", flush=True)
        return False
    except Exception as e:
        print(f"  ERROR {os.path.basename(output_path)}: {e}", flush=True)
        return False

# ── All 15 concepts ──────────────────────────────────────────────────────────

CONCEPTS = [
    # Architectural Concepts (1-3)
    ("riff_brutalist_staircase.png",
     "A polished chrome mannequin wearing the EXACT dress from IMAGE 1 (cream sleeveless maxi, thin vertical pinstripes on A-line skirt, delicate black ink chrysanthemum botanical art on bodice, chain link straps) ascending a monumental brutalist concrete staircase. The staircase spirals upward infinitely. Harsh directional light creates dramatic shadows. The dress flows behind on the stairs. Architectural fashion editorial. ONE image."),

    ("riff_cathedral.png",
     "A chrome mannequin wearing the dress from IMAGE 1 (cream maxi, thin vertical pinstripes, botanical ink bodice, chain straps) standing in an empty Gothic cathedral. Colored light streams through stained glass windows onto the cream fabric. The vertical pinstripes of the dress echo the vertical Gothic columns. Sacred meets secular fashion. ONE image."),

    ("riff_parking_garage.png",
     "A chrome mannequin wearing the dress from IMAGE 1 (thin vertical pinstripes, botanical chrysanthemum bodice, chain straps, cream maxi) standing alone in an underground parking garage. Fluorescent lights cast a green-yellow glow. Painted floor lines. Raw, unexpected fashion editorial location. Contrast between the delicate dress and the industrial concrete. ONE image."),

    # Nature/Elemental Concepts (4-6)
    ("riff_cherry_blossom.png",
     "A chrome mannequin wearing the dress from IMAGE 1 (cream maxi, thin vertical pinstripes on skirt, black ink chrysanthemum botanical bodice, chain link straps) standing under a canopy of pink cherry blossom trees. Petals fall around the mannequin like confetti. The botanical ink illustrations on the bodice rhyme with the real blossoms. Soft, dreamy, springtime editorial. ONE image."),

    ("riff_thunderstorm.png",
     "Dramatic fashion editorial. A chrome mannequin wearing the dress from IMAGE 1 (thin vertical pinstripes, botanical ink bodice, chain straps, cream maxi) stands on an exposed clifftop during a thunderstorm. Lightning illuminates the scene. The dress whips in violent wind. Dark dramatic clouds. The chrome skin reflects the lightning. Raw power meets elegance. ONE image."),

    ("riff_ice_cave.png",
     "A chrome mannequin wearing the dress from IMAGE 1 (cream sleeveless maxi, thin vertical pinstripes, botanical chrysanthemum bodice, chain straps) inside a luminous blue ice cave. Translucent ice walls glow with ethereal blue light. The warm cream dress creates a striking temperature contrast against the frozen environment. Otherworldly editorial. ONE image."),

    # Pop Culture/Art Concepts (7-9)
    ("riff_pop_art.png",
     "Andy Warhol-inspired fashion editorial. A chrome mannequin wearing the dress from IMAGE 1 (cream maxi, thin vertical pinstripes, botanical ink bodice, chain straps) against a wall of oversized Campbell's soup-style pop art cans in bright colors. Three large white smiley face balloons float in the scene. Bold, graphic, pop-art fashion. ONE image."),

    ("riff_graffiti_wall.png",
     "Street fashion editorial. A chrome mannequin wearing the dress from IMAGE 1 (thin vertical pinstripes, chrysanthemum botanical bodice, chain straps, cream maxi) leaning against a massive colorful graffiti-covered concrete wall. Urban grit meets haute couture. A single white smiley face balloon floats above. Sharp contrast between refined and raw. ONE image."),

    ("riff_vaporwave.png",
     "Vaporwave aesthetic fashion shot. A chrome mannequin wearing the dress from IMAGE 1 (cream maxi, thin vertical pinstripes, botanical ink bodice, chain link straps) in a surreal pink and teal landscape. Greek marble columns, checkered floors extending to infinity, palm trees, retro sunset. The cream dress with vertical pinstripes cuts through the digital aesthetic. Dreamy, nostalgic. ONE image."),

    # Surreal/Conceptual (10-12)
    ("riff_giant_mannequin.png",
     "Surreal scale: a GIANT 20-meter chrome mannequin wearing the dress from IMAGE 1 (cream maxi, thin vertical pinstripes, botanical bodice, chain straps) towers over a miniature city at dusk. Tiny cars and people below. The massive pinstriped skirt drapes over buildings. Two enormous white smiley face balloons float at head height. Surrealist fashion advertising. ONE image."),

    ("riff_fragmented.png",
     "Shattered mirror concept. Multiple fragments of a chrome mannequin wearing the dress from IMAGE 1 (thin vertical pinstripes, botanical chrysanthemum bodice, chain straps, cream maxi) visible in large floating shards of broken mirror against a black background. Each shard shows a different angle. Fractured beauty. Art fashion editorial. ONE image."),

    ("riff_double_exposure.png",
     "Double exposure fashion photograph. A chrome mannequin wearing the dress from IMAGE 1 (cream maxi, thin vertical pinstripes, botanical bodice, chain straps) merged with an image of chrysanthemum flowers in full bloom. The botanical ink illustrations on the bodice blend seamlessly with the real flowers in the double exposure. Ethereal, artistic, fashion-meets-nature. ONE image."),

    # Scene-Inspired Remixes (13-15)
    ("riff_grid_neon_smileys.png",
     "COMBINE all three scene themes: A chrome mannequin wearing the dress from IMAGE 1 (cream maxi, thin vertical pinstripes, botanical ink bodice, chain straps) in a half-white, half-black room. The left side is white grid tiles, the right side is black with neon blue grid lines. Vertical neon light bars at the boundary. Three white smiley face balloons float in the space. The mannequin straddles both worlds. High concept fashion editorial. ONE image."),

    ("riff_smiley_army.png",
     "An army of 50+ white smiley face balloons filling a vast white space. In the center, a single chrome mannequin wearing the dress from IMAGE 1 (cream maxi, thin vertical pinstripes, botanical chrysanthemum bodice, chain straps) stands surrounded by the floating smileys. Some smileys are huge, some tiny. The mannequin is the only non-smiley element. Maximalist surreal pop editorial. ONE image."),

    ("riff_runway.png",
     "Fashion show concept. A chrome mannequin wearing the dress from IMAGE 1 (cream sleeveless maxi, thin vertical pinstripes on A-line skirt, black ink chrysanthemum botanical bodice, thin chain link straps) walking a futuristic runway. The runway is a strip of light in darkness. Audience silhouettes on both sides. Floating white smiley face balloons serve as spotlights above. The cream dress catches the light. Fashion week meets surrealism. ONE image."),
]

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    successes = 0
    failures = 0
    total = len(CONCEPTS)

    print(f"=== EXPANDED CREATIVE RIFFS: Generating {total} images ===\n", flush=True)

    for i, (filename, prompt) in enumerate(CONCEPTS, 1):
        output_path = os.path.join(OUT_DIR, filename)
        print(f"[{i}/{total}] {filename}...", flush=True)

        ok = generate(GARMENT, prompt, output_path)
        if ok:
            successes += 1
        else:
            # One retry on failure
            print(f"  Retrying {filename}...", flush=True)
            time.sleep(3)
            ok = generate(GARMENT, prompt, output_path, attempt=2)
            if ok:
                successes += 1
            else:
                failures += 1

        # 2-second sleep between calls to avoid rate limiting
        if i < total:
            time.sleep(2)

    print(f"\n{'='*50}", flush=True)
    print(f"EXPANDED RIFFS DONE: {successes}/{total} succeeded, {failures} failed", flush=True)
    print(f"{'='*50}", flush=True)

if __name__ == "__main__":
    main()
