#!/usr/bin/env python3
"""
Generate branded Veo 3.1 fashion films for Topshop SS26 "Style Reimagined" campaign.

Uses the Veo 3.1 API (text-to-video) with 7-layer cinematic prompts inspired by
the 5 highest-quality scene riff images. After generation, applies ffmpeg branding
overlay: "STYLE REIMAGINED | TOPSHOP SS26".

API: https://generativelanguage.googleapis.com/v1beta/models/veo-3.1-generate-preview:predictLongRunning
"""

import json
import os
import subprocess
import sys
import time

try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests

# --- Configuration ---
BASE_DIR = "/home/devuser/workspace/campaign/THG-world-record-attempt"
OUT_DIR = os.path.join(BASE_DIR, "assets", "animated")
PROMPTS_FILE = os.path.join(BASE_DIR, "scripts", "veo-branded-prompts.json")
FONT_PATH = "/usr/share/fonts/noto/NotoSans-Bold.ttf"

API_KEY = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_GEMINI_API_KEY") or ""
VEO_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/veo-3.1-generate-preview:predictLongRunning?key={API_KEY}"
POLL_ENDPOINT_TPL = "https://generativelanguage.googleapis.com/v1beta/{operation_name}?key={api_key}"

# Branding overlay text
BRAND_TEXT_LINE1 = "STYLE REIMAGINED"
BRAND_TEXT_LINE2 = "TOPSHOP SS26"

# --- 7-Layer Cinematic Prompts (Camera / Lens / Subject / Action / Setting / Lighting / Style) ---
VIDEOS = [
    {
        "id": "greenhouse",
        "output_raw": "veo_greenhouse_raw.mp4",
        "output_branded": "veo_greenhouse.mp4",
        "source_image": "assets/scene-riffs/variations/riff_greenhouse.png",
        "scene_description": "Victorian greenhouse with real chrysanthemums",
        "prompt": (
            "Slow dolly push forward on an 85mm f/1.4 lens, shallow depth of field. "
            "A polished chrome mannequin wearing a cream sleeveless maxi dress with delicate "
            "black ink botanical chrysanthemum illustrations on the bodice and thin vertical "
            "pinstripes on the flowing A-line skirt stands centered in a grand Victorian "
            "greenhouse conservatory. The dress fabric sways gently in a warm draft, hem "
            "rippling subtly. Real chrysanthemum flowers in terracotta pots line iron-framed "
            "glass shelves on both sides. Warm golden afternoon sunlight streams through the "
            "glass roof panels, casting dappled botanical shadows across the cream fabric. "
            "Dust motes and pollen particles drift lazily through sunbeams. Condensation beads "
            "on glass panes. Style: High-fashion editorial, cinematic, Vogue Italia. "
            "Rich color grading with warm amber tones and jade green accents. "
            "No text, no subtitles, no watermarks. 8 seconds."
        ),
        "aspect_ratio": "9:16",
    },
    {
        "id": "neon_cityscape",
        "output_raw": "veo_neon_cityscape_raw.mp4",
        "output_branded": "veo_neon_cityscape.mp4",
        "source_image": "assets/scene-riffs/variations/riff_neon_cityscape.png",
        "scene_description": "Tokyo/Blade Runner neon rooftop",
        "prompt": (
            "Slow lateral tracking shot right to left on an 85mm f/1.4 lens, telephoto "
            "compression with heavy bokeh. A polished chrome mannequin wearing a cream "
            "sleeveless maxi dress with black ink botanical chrysanthemum art on the bodice "
            "and thin vertical pinstripes on the A-line skirt stands on a rain-slicked Tokyo "
            "rooftop at night. The cream dress fabric flutters gently in the urban wind. "
            "Behind, a vast neon cityscape stretches to the horizon -- Blade Runner aesthetic "
            "with electric pink, cyan, and violet holographic billboards. Rain falls through "
            "neon light cones as silver streaks. Puddles on the concrete rooftop reflect the "
            "neon palette in long vertical streaks. The chrome mannequin surface catches and "
            "refracts the surrounding neon colors. Style: Cyberpunk high-fashion editorial, "
            "cinematic, W Magazine meets Ridley Scott. Cool blue-violet color grade with "
            "electric accent pops. No text, no subtitles, no watermarks. 8 seconds."
        ),
        "aspect_ratio": "9:16",
    },
    {
        "id": "neon_emerge",
        "output_raw": "veo_neon_emerge_raw.mp4",
        "output_branded": "veo_neon_emerge.mp4",
        "source_image": "assets/scene-riffs/composited/composite_neon_emerge.png",
        "scene_description": "Neon corridor emergence",
        "prompt": (
            "Slow forward dolly on an 85mm f/1.4 lens, one-point perspective vanishing point. "
            "A polished chrome mannequin wearing a cream sleeveless maxi dress with black ink "
            "botanical chrysanthemum illustrations on the bodice and thin vertical pinstripes "
            "on the A-line skirt emerges from a dark corridor flanked by vertical neon light "
            "bars in teal and electric blue. The dress fabric catches the neon glow, cream "
            "fabric luminous against the darkness. The mannequin walks forward with measured "
            "confident strides, skirt swaying with each step. Volumetric haze drifts through "
            "the corridor, neon light rays cutting through the atmospheric fog. The polished "
            "concrete floor reflects the neon bars as elongated streaks. Rim lighting outlines "
            "the chrome mannequin silhouette in electric blue. Style: High-fashion editorial "
            "meets sci-fi cinema, Alexander McQueen runway energy. Dark moody color grade with "
            "teal and cobalt accents. No text, no subtitles, no watermarks. 8 seconds."
        ),
        "aspect_ratio": "16:9",
    },
    {
        "id": "mirror_room",
        "output_raw": "veo_mirror_room_raw.mp4",
        "output_branded": "veo_mirror_room.mp4",
        "source_image": "assets/scene-riffs/variations/flux2_mirror_room.png",
        "scene_description": "Kusama-inspired infinity mirror room",
        "prompt": (
            "Slow orbit tracking shot circling the subject on an 85mm f/1.4 lens, shallow "
            "depth of field with infinite reflections stretching to vanishing points. A polished "
            "chrome mannequin wearing a cream sleeveless maxi dress with black ink botanical "
            "chrysanthemum art on the bodice and thin vertical pinstripes on the A-line skirt "
            "stands in the center of a Yayoi Kusama-inspired infinity mirror room. Hundreds "
            "of small warm LED light orbs float at varying heights, reflected infinitely in "
            "every mirror surface. The chrome mannequin multiplies endlessly in the mirrors. "
            "The cream dress glows warmly under the ambient LED orbs. The skirt hem drifts "
            "gently as if in a slow air current. Mirror reflections create a kaleidoscopic "
            "tunnel of fashion and light extending in all directions. Style: High-fashion "
            "editorial meets contemporary art installation, i-D Magazine aesthetic. Warm amber "
            "and soft pink color grade. No text, no subtitles, no watermarks. 8 seconds."
        ),
        "aspect_ratio": "16:9",
    },
    {
        "id": "cherry_blossom",
        "output_raw": "veo_cherry_blossom_raw.mp4",
        "output_branded": "veo_cherry_blossom.mp4",
        "source_image": "assets/scene-riffs/variations/riff_cherry_blossom.png",
        "scene_description": "Cherry blossom petals falling",
        "prompt": (
            "Slow upward tilt from hem to face on an 85mm f/1.4 lens, extremely shallow "
            "depth of field with creamy bokeh. A polished chrome mannequin wearing a cream "
            "sleeveless maxi dress with black ink botanical chrysanthemum illustrations on "
            "the bodice and thin vertical pinstripes on the flowing A-line skirt stands beneath "
            "a canopy of pale pink cherry blossom trees in full bloom. Hundreds of cherry "
            "blossom petals drift and spiral slowly downward through the frame, some landing "
            "on the cream fabric of the dress and settling on the chrome shoulders. A gentle "
            "spring breeze causes the dress hem to billow softly. Soft diffused afternoon "
            "light filters through the blossom canopy, casting delicate dappled shadows across "
            "the dress. The ground is carpeted with fallen pink petals. The chrome surface "
            "reflects soft pink tones from the surrounding blossoms. Style: High-fashion "
            "editorial, ethereal and romantic, Harper's Bazaar Japan aesthetic. Soft pastel "
            "color grade with blush pink and ivory tones. No text, no subtitles, no watermarks. "
            "8 seconds."
        ),
        "aspect_ratio": "9:16",
    },
]


def save_prompts_json():
    """Save all prompts to JSON for manual execution if API fails."""
    prompts_data = {
        "campaign": "Topshop SS26 - Style Reimagined",
        "model": "veo-3.1-generate-preview",
        "method": "predictLongRunning (text-to-video)",
        "duration_seconds": 8,
        "branding": f"{BRAND_TEXT_LINE1} | {BRAND_TEXT_LINE2}",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "endpoint": "https://generativelanguage.googleapis.com/v1beta/models/veo-3.1-generate-preview:predictLongRunning",
        "videos": []
    }
    for v in VIDEOS:
        prompts_data["videos"].append({
            "id": v["id"],
            "scene_description": v["scene_description"],
            "source_image": v["source_image"],
            "output_file": v["output_branded"],
            "aspect_ratio": v["aspect_ratio"],
            "prompt": v["prompt"],
            "api_payload": {
                "instances": [{"prompt": v["prompt"]}],
                "parameters": {
                    "aspectRatio": v["aspect_ratio"],
                    "durationSeconds": 8,
                    "sampleCount": 1
                }
            }
        })
    with open(PROMPTS_FILE, "w") as f:
        json.dump(prompts_data, f, indent=2)
    print(f"Saved prompts to {PROMPTS_FILE}")
    return prompts_data


def submit_veo_job(prompt, aspect_ratio):
    """Submit a Veo 3.1 video generation job. Returns operation name or None."""
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {
            "aspectRatio": aspect_ratio,
            "durationSeconds": 8
        }
    }
    try:
        resp = requests.post(VEO_ENDPOINT, json=payload, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            op_name = data.get("name", "")
            if op_name:
                print(f"  Job submitted: {op_name}")
                return op_name
            else:
                print(f"  Unexpected response (no operation name): {json.dumps(data)[:300]}")
                return None
        else:
            print(f"  API error {resp.status_code}: {resp.text[:500]}")
            return None
    except Exception as e:
        print(f"  Request failed: {e}")
        return None


def poll_veo_job(operation_name, max_wait=600, poll_interval=15):
    """Poll a Veo long-running operation until done. Returns video URI or None."""
    url = POLL_ENDPOINT_TPL.format(operation_name=operation_name, api_key=API_KEY)
    start = time.time()
    while time.time() - start < max_wait:
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code != 200:
                print(f"    Poll error {resp.status_code}: {resp.text[:300]}")
                time.sleep(poll_interval)
                continue

            data = resp.json()
            done = data.get("done", False)

            if done:
                # Check for error
                if "error" in data:
                    err = data["error"]
                    print(f"    Job failed: {err.get('message', str(err))}")
                    return None

                # Log response structure for debugging
                response_data = data.get("response", {})
                print(f"    Response keys: {list(response_data.keys())}")

                # Extract video URI from response -- try multiple structures
                videos = response_data.get("generateVideoResponse", {}).get("generatedSamples", [])
                if not videos:
                    videos = response_data.get("generatedSamples", [])
                if not videos:
                    predictions = response_data.get("predictions", [])
                    if predictions:
                        video_uri = predictions[0].get("videoUri", "") or predictions[0].get("video", {}).get("uri", "")
                        if video_uri:
                            print(f"    Video URI: {video_uri[:120]}...")
                            return video_uri

                if videos:
                    video = videos[0]
                    print(f"    Sample keys: {list(video.keys())}")
                    video_uri = video.get("video", {}).get("uri", "") or video.get("videoUri", "")
                    if video_uri:
                        print(f"    Video URI: {video_uri[:120]}...")
                        return video_uri

                print(f"    Job done but no video URI found. Full response: {json.dumps(data)[:800]}")
                return None

            # Not done yet
            elapsed = int(time.time() - start)
            print(f"    Waiting... ({elapsed}s elapsed)")
            time.sleep(poll_interval)

        except Exception as e:
            print(f"    Poll exception: {e}")
            time.sleep(poll_interval)

    print(f"    Timed out after {max_wait}s")
    return None


def download_video(uri, output_path):
    """Download video from URI. Appends API key if it's a Google API URL."""
    # If the URI is a Google API endpoint, append the API key
    download_url = uri
    if "googleapis.com" in uri:
        separator = "&" if "?" in uri else "?"
        download_url = f"{uri}{separator}key={API_KEY}"

    try:
        result = subprocess.run(
            ["curl", "-L", "-s", "-o", output_path, download_url],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0 and os.path.exists(output_path):
            size_bytes = os.path.getsize(output_path)
            # Check if the download is actually a video (> 10KB) or an error response
            if size_bytes < 10000:
                # Likely an error, check content
                try:
                    with open(output_path, "r") as f:
                        content = f.read(2000)
                    if content.strip().startswith("{") and "error" in content:
                        print(f"    Download returned error: {content[:300]}")
                        os.remove(output_path)
                        return False
                except Exception:
                    pass
            size_kb = size_bytes // 1024
            print(f"    Downloaded: {output_path} ({size_kb}KB)")
            return True
        else:
            print(f"    Download failed: {result.stderr[:200]}")
            return False
    except Exception as e:
        print(f"    Download exception: {e}")
        return False


def add_branding(input_path, output_path):
    """Add 'STYLE REIMAGINED | TOPSHOP SS26' text overlay using ffmpeg."""
    # Get video dimensions
    probe_cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0",
        input_path
    ]
    try:
        probe = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=15)
        dims = probe.stdout.strip().split(",")
        width = int(dims[0])
        height = int(dims[1])
    except Exception:
        width, height = 1080, 1920  # fallback

    # Calculate font sizes relative to video width
    font_size_1 = max(24, int(width * 0.04))
    font_size_2 = max(18, int(width * 0.028))
    border_w = max(2, int(font_size_1 * 0.06))

    # Position: bottom center with padding
    y_offset_1 = int(height * 0.88)
    y_offset_2 = y_offset_1 + font_size_1 + int(font_size_1 * 0.4)

    # Build ffmpeg drawtext filter -- two lines, escaping colons in text with \\:
    text1_escaped = BRAND_TEXT_LINE1.replace(":", "\\:")
    text2_escaped = BRAND_TEXT_LINE2.replace(":", "\\:")

    filter_str = (
        f"drawtext=text='{text1_escaped}':"
        f"fontfile='{FONT_PATH}':"
        f"fontsize={font_size_1}:"
        f"fontcolor=white:"
        f"borderw={border_w}:"
        f"bordercolor=black@0.5:"
        f"x=(w-text_w)/2:"
        f"y={y_offset_1}:"
        f"enable='between(t\\,1\\,7.5)',"
        f"drawtext=text='{text2_escaped}':"
        f"fontfile='{FONT_PATH}':"
        f"fontsize={font_size_2}:"
        f"fontcolor=white@0.85:"
        f"borderw={border_w}:"
        f"bordercolor=black@0.4:"
        f"x=(w-text_w)/2:"
        f"y={y_offset_2}:"
        f"enable='between(t\\,1\\,7.5)'"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", filter_str,
        "-codec:a", "copy",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        output_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0 and os.path.exists(output_path):
            size_kb = os.path.getsize(output_path) // 1024
            print(f"    Branded: {output_path} ({size_kb}KB)")
            return True
        else:
            print(f"    Branding failed: {result.stderr[:500]}")
            return False
    except Exception as e:
        print(f"    Branding exception: {e}")
        return False


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # Always save prompts JSON first
    prompts_data = save_prompts_json()

    # Check API key
    if not API_KEY:
        print("\nNo GOOGLE_API_KEY or GOOGLE_GEMINI_API_KEY found in environment.")
        print(f"Prompts saved to {PROMPTS_FILE} for manual execution.")
        print("Set the API key and re-run, or use the prompts JSON with curl.")
        return

    print(f"\nAPI Key: ...{API_KEY[-8:]}")
    print(f"Endpoint: {VEO_ENDPOINT[:80]}...")
    print(f"Output: {OUT_DIR}")
    print(f"Videos to generate: {len(VIDEOS)}")
    print("=" * 70)

    results = {}
    for i, video in enumerate(VIDEOS, 1):
        print(f"\n[{i}/{len(VIDEOS)}] {video['id']} -- {video['scene_description']}")
        print(f"  Aspect: {video['aspect_ratio']}, Duration: 8s")

        raw_path = os.path.join(OUT_DIR, video["output_raw"])
        branded_path = os.path.join(OUT_DIR, video["output_branded"])

        # Resume support: skip if branded file already exists and is valid
        if os.path.exists(branded_path) and os.path.getsize(branded_path) > 50000:
            size_mb = os.path.getsize(branded_path) / (1024 * 1024)
            print(f"  SKIP: Already exists ({size_mb:.1f}MB)")
            results[video["id"]] = "already_exists"
            continue

        # Step 1: Submit job with rate-limit retry
        op_name = None
        for attempt in range(1, 4):
            op_name = submit_veo_job(video["prompt"], video["aspect_ratio"])
            if op_name:
                break
            # If rate limited, wait and retry
            wait_time = 60 * attempt
            print(f"  Retrying in {wait_time}s (attempt {attempt}/3)...")
            time.sleep(wait_time)

        if not op_name:
            print(f"  FAILED: Could not submit job after retries")
            results[video["id"]] = "submit_failed"
            continue

        # Step 2: Poll for completion
        print(f"  Polling for completion (up to 10 min)...")
        video_uri = poll_veo_job(op_name, max_wait=600, poll_interval=15)
        if not video_uri:
            print(f"  FAILED: Job did not complete or no video URI")
            results[video["id"]] = "generation_failed"
            continue

        # Step 3: Download
        print(f"  Downloading video...")
        if not download_video(video_uri, raw_path):
            results[video["id"]] = "download_failed"
            continue

        # Step 4: Add branding overlay
        print(f"  Adding branding overlay...")
        if add_branding(raw_path, branded_path):
            results[video["id"]] = "success"
            # Remove raw file to save space
            try:
                os.remove(raw_path)
            except Exception:
                pass
        else:
            # If branding fails, keep the raw file as the output
            print(f"  Branding failed, keeping raw video as output")
            try:
                os.rename(raw_path, branded_path)
                results[video["id"]] = "success_no_brand"
            except Exception:
                results[video["id"]] = "brand_failed"

        # Pause between API calls
        if i < len(VIDEOS):
            print("  Waiting 10s before next submission...")
            time.sleep(10)

    # Summary
    print("\n" + "=" * 70)
    print("VEO 3.1 BRANDED VIDEO GENERATION SUMMARY")
    print("=" * 70)
    success_count = 0
    for video in VIDEOS:
        status = results.get(video["id"], "not_attempted")
        icon = "OK" if "success" in status else "FAIL"
        print(f"  [{icon}] {video['output_branded']}: {status}")
        branded_path = os.path.join(OUT_DIR, video["output_branded"])
        if os.path.exists(branded_path):
            size_mb = os.path.getsize(branded_path) / (1024 * 1024)
            print(f"        Size: {size_mb:.1f}MB")
            success_count += 1

    print(f"\nResults: {success_count}/{len(VIDEOS)} videos generated")
    print(f"Prompts: {PROMPTS_FILE}")
    print(f"Output:  {OUT_DIR}")


if __name__ == "__main__":
    main()
