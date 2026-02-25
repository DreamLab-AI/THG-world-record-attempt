# Veo 3.1 Fashion Video Recipes

Best practices and prompt recipes for fashion advertising video generation.
API Key: `$GOOGLE_API_KEY` (via Vertex AI)

---

## Veo 3.1 Capabilities

| Feature | Specification |
|---------|--------------|
| Resolution | 720p or 1080p |
| Frame Rate | 24 fps |
| Duration | 4, 6, or 8 seconds per clip |
| Extended | Up to 2 minutes with "Extend" feature |
| Modes | Text-to-Video (T2V), Image-to-Video (I2V) |
| Audio | Synchronized audio generation from prompt |
| Aspect Ratios | 9:16 (vertical), 16:9 (horizontal) |

---

## Prompting Framework

### The 7-Layer Master Template

```
[Camera move + lens]: [Subject] [Action & physics],
in [Setting + atmosphere], lit by [Light source].
Style: [Texture/finish]. Audio: [Dialogue/SFX/ambience].
```

### Camera and Lens Reference

| Lens | Effect | Best For |
|------|--------|----------|
| 16mm | Expands space, dramatic | Wide establishing shots |
| 24mm | Slight expansion, environmental | Lifestyle context |
| 35mm | Natural perspective | Standard fashion |
| 50mm | Natural, minimal distortion | Portraits, detail |
| 85mm | Compressed background, intimacy | Close-up, editorial |
| 135mm | Strong compression, bokeh | Isolated subject, runway |

### Motion Verbs (Force-Based for Realism)

Use: push, pull, sway, ripple, spiral, drift, glide, settle, flutter, billow

Avoid: move, go, do (too vague)

---

## Fashion Advertising Video Recipes

### Recipe 1: Runway Walk (Full Body)

```
Slow dolly tracking right on a 85mm lens. A fashion model in a [GARMENT DESCRIPTION]
walks confidently down a minimalist runway. White concrete floor, neutral backdrop.
The fabric [sways/billows/drapes] with each measured step. High-key studio lighting,
soft shadows pool at the feet. Style: Clean, modern, aspirational. Audio: Soft
footstep clicks on concrete, faint ambient crowd murmur. No subtitles.
```

**Settings:** 16:9, 8 seconds, 1080p

### Recipe 2: Garment Detail Hero Shot

```
Camera locked at waist level, 50mm macro lens. Extreme close-up on [GARMENT DETAIL:
buttons, stitching, fabric weave, collar construction]. The fabric catches soft
studio light and creates subtle shifting highlights as the model breathes naturally.
Shallow depth of field, background dissolved into cream bokeh. Style: Tactile,
luxurious, slow. Audio: Quiet fabric rustle, ambient studio tone. No subtitles.
```

**Settings:** 16:9, 6 seconds, 1080p

### Recipe 3: Editorial Portrait (Subtle Motion)

```
Camera locked at eye level, medium close-up on a 85mm lens. A model with [FEATURES]
wearing [GARMENT DESCRIPTION] looks directly at camera. Minimal movement: gentle
breathing, slight wind in hair, fabric edge flutters once. Soft daylight from a
side window, gentle fill on the opposite side, natural falloff. Style: High-end
fashion editorial, cinematic grain. Audio: Gentle ambient breeze. No subtitles.
```

**Settings:** 9:16, 6 seconds, 1080p

### Recipe 4: Lifestyle Fashion Moment

```
Slow forward push on a 35mm lens. A [PERSON DESCRIPTION] wearing [GARMENT] sits
at a marble cafe table, lifts a ceramic coffee cup to their lips and smiles slightly.
Morning golden hour light streams through large windows, casting warm geometric
shadows. Urban cafe interior, blurred pedestrians through glass behind.
Style: Aspirational lifestyle, warm grade. Audio: Quiet cafe ambience, distant
conversation murmur, cup-on-saucer clink. No subtitles.
```

**Settings:** 16:9, 8 seconds, 1080p

### Recipe 5: Product Reveal

```
Slow zoom-in starting from medium shot to close-up, 50mm lens. [GARMENT] displayed
on a rotating glass turntable against a dark charcoal backdrop. Single key light
from upper left reveals fabric texture and construction details progressively.
One full 90-degree rotation over the clip duration. Style: Premium product reveal,
luxury brand aesthetic. Audio: Soft ambient tone, subtle mechanical turntable hum.
No subtitles.
```

**Settings:** 1:1 or 16:9, 8 seconds, 1080p

### Recipe 6: Campaign Statement (With Audio)

```
Slow lateral tracking left on a 35mm lens. A model in [GARMENT DESCRIPTION] stands
against a [BACKDROP]. Confident posture, slight head turn toward camera at the
midpoint. High-key studio light, soft shadows. The model says: "[SHORT TAGLINE,
5-8 words max]." Style: Fashion campaign, clean and bold. Audio: Model's voice
clear and centered, subtle reverb. No subtitles.
```

**Settings:** 16:9, 8 seconds, 1080p

### Recipe 7: Fabric in Motion (B-Roll)

```
Camera locked, 135mm telephoto lens. Extreme slow motion feeling. A swatch of
[FABRIC TYPE] in [COLOR] ripples in a gentle breeze against a [BACKGROUND].
Light plays across the surface, revealing texture and sheen. The fabric moves
in a slow wave pattern left to right. Style: Abstract, textural, premium.
Audio: Soft wind, fabric whisper. No subtitles.
```

**Settings:** 16:9, 6 seconds, 1080p

---

## Keeping Text Static While Animating Background

Veo 3.1 does not natively support text layer locking. Use this workaround:

### Method: Image-to-Video with Pre-Rendered Text

1. **Generate the base image** (via Flux 2 or Nano Banana Pro) with text already composited
2. **Use Veo I2V mode** with a motion-restricted prompt:

```
The background shifts with subtle ambient motion -- gentle light play, soft shadow
movement -- while the foreground subject and all text elements remain completely
static and locked in place. Camera is locked, no camera movement. Only environmental
elements in the far background show gentle motion: light shifts, subtle particles.
The text and model are frozen in position. No subtitles, no additional text.
```

3. **Key phrases for text stability:**
   - "Camera is locked, no camera movement"
   - "Text remains completely static"
   - "Foreground elements remain frozen in position"
   - "Only background shows subtle motion"

### Alternative: Post-Processing Composite

1. Generate a video with Veo (no text)
2. Overlay text in post-production using FFmpeg:

```bash
ffmpeg -i veo_output.mp4 \
  -vf "drawtext=text='BRAND NAME':fontfile=font.ttf:fontsize=72:fontcolor=white:x=(w-text_w)/2:y=h*0.1" \
  -codec:a copy \
  output_with_text.mp4
```

---

## Timestamp Prompting (Scene Choreography)

Control progression within a single continuous shot:

```
0-3 seconds: Wide shot of empty studio space, key light slowly fading up
from darkness, revealing a polished concrete floor.
3-6 seconds: A model in [GARMENT] steps into frame from the right,
stops at center mark. Fabric settles from movement.
6-8 seconds: Slow push-in to medium close-up as model turns chin
slightly toward camera. Final pose holds.
```

---

## Clip Chaining (Multi-Clip Sequences)

For sequences longer than 8 seconds:

1. Generate Clip 1
2. Extract the final frame of Clip 1
3. Use that frame as the I2V input for Clip 2
4. Continue the motion description from where Clip 1 ended

This maintains:
- Camera position consistency
- Lighting continuity
- Subject identity across clips
- Wardrobe consistency

---

## API Usage

### Via ComfyUI (Recommended)

Use the official Google GenMedia custom nodes (see recommended-custom-nodes.md).

### Via Direct API (Vertex AI)

```bash
# Text-to-Video
curl -X POST \
  "https://${REGION}-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${REGION}/publishers/google/models/veo-3.1:predictLongRunning" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -d '{
    "instances": [{
      "prompt": "YOUR PROMPT HERE"
    }],
    "parameters": {
      "aspectRatio": "16:9",
      "durationSeconds": 8,
      "resolution": "1080p",
      "personGeneration": "allow_adult"
    }
  }'
```

### Via Gemini API (Simpler)

```bash
curl -s -X POST \
  "https://generativelanguage.googleapis.com/v1beta/models/veo-3.1:generateVideo" \
  -H "x-goog-api-key: $GOOGLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{
      "parts": [{
        "text": "YOUR PROMPT HERE"
      }]
    }],
    "generationConfig": {
      "aspectRatio": "16:9",
      "durationSeconds": 8
    }
  }'
```

---

## Prompt Anti-Patterns (Avoid These)

| Bad | Good | Why |
|-----|------|-----|
| "Video of a woman in a dress" | "Slow dolly right on 85mm. A model in a flowing silk midi dress..." | Vague vs. directional |
| "Five people walking" | "A small group walks down the street" | Exact counts cause artifacts |
| "Beautiful fashion video" | "High-key studio light, 35mm lens, model turns chin toward camera" | Subjective vs. technical |
| "Add text that says BRAND" | Pre-render text in source image, use I2V | Veo cannot reliably render text |
| Multiple conflicting actions | One dominant movement per clip | Stacking causes confusion |

---

## Negative Prompting

Block unwanted elements:

```
... [your main prompt]. No subtitles, no text overlays, no watermarks,
no split-screen, no collage effect, no sci-fi elements, no surreal distortions.
```

---

## References

- [Ultimate Prompting Guide for Veo 3.1 - Google Cloud](https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-veo-3-1)
- [Veo 3.1 Prompt Guide - Invideo](https://invideo.io/blog/google-veo-prompt-guide/)
- [Best Veo 3 Prompts 2025](https://skywork.ai/blog/best-veo-3-prompts-2025/)
- [Veo 3 for Marketers](https://www.godofprompt.ai/blog/veo-3-prompts-for-marketer)
- [Veo 3.1 in ComfyUI](https://blog.comfy.org/p/veo-31-is-now-available-in-comfyui)
- [Google GenMedia Custom Nodes](https://github.com/GoogleCloudPlatform/comfyui-google-genmedia-custom-nodes)
- [Veo 3 JSON Prompt Examples](https://jzcreates.com/blog/7-incredible-google-veo-3-json-prompt-examples/)
