#!/usr/bin/env python3
"""
Flux 2 Dev Local Generation via ComfyUI (dual RTX 6000 Ada GPUs)
Generates 8 diverse editorial scene variations for the THG world record campaign.
"""

import requests, json, time, os, urllib.parse, shutil, sys

COMFY_URL = "http://comfyui:8188"
OUTPUT_DIR = "/home/devuser/workspace/campaign/THG-world-record-attempt/assets/scene-riffs/variations/"

os.makedirs(OUTPUT_DIR, exist_ok=True)


def make_workflow(prompt_text, seed=42, width=1024, height=1024, steps=20):
    """Build a ComfyUI workflow dict for Flux 2 Dev multi-GPU generation."""
    return {
        "1": {
            "class_type": "UNETLoaderMultiGPU",
            "inputs": {
                "unet_name": "flux2_dev_fp8mixed.safetensors",
                "weight_dtype": "default",
                "device": "cuda:0"
            }
        },
        "2": {
            "class_type": "CLIPLoaderMultiGPU",
            "inputs": {
                "clip_name": "mistral_3_small_flux2_fp8.safetensors",
                "type": "flux2",
                "device": "cuda:1"
            }
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": prompt_text,
                "clip": ["2", 0]
            }
        },
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "",
                "clip": ["2", 0]
            }
        },
        "5": {
            "class_type": "EmptySD3LatentImage",
            "inputs": {
                "width": width,
                "height": height,
                "batch_size": 1
            }
        },
        "6": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0],
                "positive": ["3", 0],
                "negative": ["4", 0],
                "latent_image": ["5", 0],
                "seed": seed,
                "steps": steps,
                "cfg": 1.0,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1.0
            }
        },
        "7": {
            "class_type": "VAELoaderMultiGPU",
            "inputs": {
                "vae_name": "flux2-vae.safetensors",
                "device": "cuda:1"
            }
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["6", 0],
                "vae": ["7", 0]
            }
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["8", 0],
                "filename_prefix": "flux2_riff"
            }
        }
    }


def submit_and_wait(workflow, timeout=600):
    """Submit a workflow to ComfyUI and wait for the result image."""
    resp = requests.post(f"{COMFY_URL}/prompt", json={"prompt": workflow}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    prompt_id = data["prompt_id"]
    print(f"  Submitted prompt_id: {prompt_id}")

    start = time.time()
    while time.time() - start < timeout:
        try:
            hist = requests.get(f"{COMFY_URL}/history/{prompt_id}", timeout=10).json()
        except Exception as e:
            print(f"  (history poll error: {e}, retrying...)")
            time.sleep(5)
            continue

        if prompt_id in hist:
            # Check for errors
            status_info = hist[prompt_id].get("status", {})
            if status_info.get("status_str") == "error":
                msgs = status_info.get("messages", [])
                print(f"  ERROR from ComfyUI: {msgs}")
                return None

            outputs = hist[prompt_id].get("outputs", {})
            for node_id, node_out in outputs.items():
                if "images" in node_out:
                    return node_out["images"][0]  # {filename, subfolder, type}
            # If we got history but no images, might be an error
            print(f"  Warning: prompt completed but no images found in outputs")
            print(f"  Outputs keys: {list(outputs.keys())}")
            return None
        time.sleep(3)

    print(f"  TIMEOUT after {timeout}s waiting for prompt {prompt_id}")
    return None


def download_image(image_info, save_path):
    """Download a generated image from ComfyUI and save to disk."""
    params = urllib.parse.urlencode({
        "filename": image_info["filename"],
        "subfolder": image_info.get("subfolder", ""),
        "type": image_info.get("type", "output")
    })
    resp = requests.get(f"{COMFY_URL}/view?{params}", timeout=30)
    resp.raise_for_status()
    with open(save_path, "wb") as f:
        f.write(resp.content)
    size_kb = len(resp.content) // 1024
    print(f"  Saved: {save_path} ({size_kb}KB)")
    return True


# ── The 8 Flux 2 editorial prompts ──────────────────────────────────────────

PROMPTS = [
    {
        "name": "flux2_smiley_warehouse",
        "seed": 100,
        "width": 1248,
        "height": 832,
        "prompt": (
            "Professional fashion editorial photograph. A polished chrome mannequin "
            "wearing a cream sleeveless A-line maxi dress with thin vertical pinstripes "
            "on the flowing skirt and delicate black ink botanical chrysanthemum "
            "illustrations on the bodice. Thin chain link straps. The mannequin stands "
            "in an industrial white warehouse. Giant white spherical smiley face balloons "
            "float in the air around it. Clean concrete floor. Overhead industrial "
            "lighting. Surreal pop fashion campaign. Shot on Hasselblad medium format."
        ),
    },
    {
        "name": "flux2_neon_alley",
        "seed": 200,
        "width": 832,
        "height": 1248,
        "prompt": (
            "Cinematic fashion photography. A polished chrome mannequin wearing a cream "
            "sleeveless maxi dress with thin vertical pinstripes on the A-line skirt and "
            "delicate black ink chrysanthemum botanical illustrations on the bodice. Thin "
            "chain link straps. Standing in a dark urban alley at night. Neon signs in "
            "blue and magenta reflecting off wet pavement. Dramatic rim lighting on the "
            "chrome body. Moody, atmospheric, high-fashion editorial. Shot on 85mm lens, "
            "shallow depth of field."
        ),
    },
    {
        "name": "flux2_white_void",
        "seed": 300,
        "width": 1024,
        "height": 1024,
        "prompt": (
            "Minimalist fashion photograph. A polished chrome mannequin wearing a cream "
            "sleeveless A-line maxi dress with thin vertical pinstripes on the skirt and "
            "black ink chrysanthemum botanical art on the bodice. Thin chain link straps. "
            "Standing in an infinite white void with soft even lighting. Three large white "
            "spherical balloons with blue smiley faces painted on them float nearby. The "
            "dress and mannequin are the only colored elements. Clean, editorial, stark."
        ),
    },
    {
        "name": "flux2_mirror_room",
        "seed": 400,
        "width": 1248,
        "height": 832,
        "prompt": (
            "Fashion editorial in an infinity mirror room. A polished chrome mannequin "
            "wearing a cream sleeveless maxi dress with thin vertical pinstripes and "
            "black ink chrysanthemum botanical bodice illustrations. Chain link straps. "
            "The mannequin stands in a hexagonal mirror room, reflecting infinitely in "
            "all directions. LED strips line the mirrors. The vertical pinstripes create "
            "mesmerizing repeating patterns in the reflections. Yayoi Kusama inspired "
            "fashion art."
        ),
    },
    {
        "name": "flux2_rain_grid",
        "seed": 500,
        "width": 832,
        "height": 1248,
        "prompt": (
            "Fashion photography in the rain. A chrome mannequin wearing a cream "
            "sleeveless A-line maxi dress with thin vertical pinstripes on the flowing "
            "skirt and delicate black ink chrysanthemum botanical illustrations on the "
            "bodice. Chain link straps. Standing in heavy rain inside a white tiled grid "
            "room. The tiles are wet and reflective. Rain streams down. Two white smiley "
            "face balloons float despite the rain. Dramatic, surreal, high-contrast. "
            "Shot on medium format."
        ),
    },
    {
        "name": "flux2_subway",
        "seed": 600,
        "width": 1248,
        "height": 832,
        "prompt": (
            "Urban fashion editorial. A polished chrome mannequin wearing a cream "
            "sleeveless maxi dress with thin vertical pinstripes on the A-line skirt and "
            "black ink chrysanthemum botanical art on the bodice. Thin chain link straps. "
            "Standing alone on an empty white-tiled subway platform. Fluorescent lighting. "
            "Train tracks in foreground. A single white smiley face balloon floats near "
            "the ceiling. Eerie, liminal space fashion photography. Wide angle."
        ),
    },
    {
        "name": "flux2_concert",
        "seed": 700,
        "width": 832,
        "height": 1248,
        "prompt": (
            "Concert fashion editorial. A polished chrome mannequin wearing a cream "
            "sleeveless A-line maxi dress with thin vertical pinstripes and black ink "
            "chrysanthemum botanical bodice illustrations. Chain link straps. Standing on "
            "a dark stage. Dramatic spotlight from above. Volumetric fog. Colored laser "
            "beams slice through the darkness in the background. The cream dress glows in "
            "the spotlight. Dramatic, rock-and-roll meets haute couture."
        ),
    },
    {
        "name": "flux2_greenhouse",
        "seed": 800,
        "width": 1024,
        "height": 1024,
        "prompt": (
            "Fashion editorial in a Victorian greenhouse. A polished chrome mannequin "
            "wearing a cream sleeveless maxi dress with thin vertical pinstripes on the "
            "A-line skirt and delicate black ink chrysanthemum botanical illustrations on "
            "the bodice. Thin chain link straps. Standing among lush green plants and "
            "real chrysanthemum flowers. Dappled sunlight through glass ceiling. The "
            "botanical ink on the dress mirrors the real flowers. Nature meets artifice. "
            "Warm, organic, beautiful."
        ),
    },
]


def main():
    print("=" * 70)
    print("FLUX 2 DEV LOCAL GENERATION via ComfyUI")
    print(f"Output: {OUTPUT_DIR}")
    print(f"Generating {len(PROMPTS)} editorial variations...")
    print("=" * 70)

    success_count = 0
    failed = []

    for i, p in enumerate(PROMPTS, 1):
        name = p["name"]
        filename = f"{name}.png"
        save_path = os.path.join(OUTPUT_DIR, filename)

        print(f"\n[{i}/{len(PROMPTS)}] {name} ({p['width']}x{p['height']}, seed={p['seed']})")
        print(f"  Prompt: {p['prompt'][:80]}...")

        workflow = make_workflow(
            prompt_text=p["prompt"],
            seed=p["seed"],
            width=p["width"],
            height=p["height"],
            steps=20,
        )

        image_info = submit_and_wait(workflow, timeout=600)

        if image_info:
            try:
                download_image(image_info, save_path)
                success_count += 1
            except Exception as e:
                print(f"  DOWNLOAD FAILED: {e}")
                failed.append(name)
        else:
            print(f"  GENERATION FAILED for {name}")
            failed.append(name)

    print("\n" + "=" * 70)
    print(f"FLUX2 RIFFS DONE -- {success_count}/{len(PROMPTS)} generated successfully")
    if failed:
        print(f"Failed: {', '.join(failed)}")
    print("=" * 70)

    # List output files
    print("\nOutput files:")
    for f in sorted(os.listdir(OUTPUT_DIR)):
        if f.startswith("flux2_"):
            fpath = os.path.join(OUTPUT_DIR, f)
            size = os.path.getsize(fpath) // 1024
            print(f"  {f} ({size}KB)")

    return 0 if success_count == len(PROMPTS) else 1


if __name__ == "__main__":
    sys.exit(main())
