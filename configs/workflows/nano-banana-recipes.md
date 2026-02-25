# Nano Banana (Gemini 2.5 Flash Image) Recipes

Best practices and prompt recipes for fashion editorial photography.
API Key: `$GOOGLE_API_KEY`

---

## API Configuration

### Model Endpoints

| Model | Endpoint | Use Case |
|-------|----------|----------|
| **Nano Banana** | `gemini-2.5-flash-image` | Fast iteration, drafts, A/B testing |
| **Nano Banana Pro** | `gemini-3-pro-image-preview` | Final assets, text overlays, production |

### Supported Aspect Ratios

| Ratio | Use Case |
|-------|----------|
| 1:1 | Instagram feed, product square |
| 2:3 | Pinterest, portrait |
| 3:2 | Landscape editorial |
| 3:4 | Standard portrait |
| 4:3 | Catalog landscape |
| 4:5 | Instagram portrait |
| 5:4 | Print editorial |
| 9:16 | Instagram Story, TikTok, Reels |
| 16:9 | YouTube thumbnail, web banner |
| 21:9 | Ultrawide banner |

### Resolution Tiers (Pro Only)

| Tier | Best For |
|------|----------|
| 1K | Drafts, social media |
| 2K | Web, editorial |
| 4K | Print, large format |

---

## Basic API Calls

### Text-to-Image (curl)

```bash
curl -s -X POST \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent" \
  -H "x-goog-api-key: $GOOGLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{
      "parts": [{
        "text": "YOUR PROMPT HERE"
      }]
    }],
    "generationConfig": {
      "responseModalities": ["TEXT", "IMAGE"]
    }
  }' | python3 -c "
import json, sys, base64
resp = json.load(sys.stdin)
for part in resp['candidates'][0]['content']['parts']:
    if 'inlineData' in part:
        with open('output.png', 'wb') as f:
            f.write(base64.b64decode(part['inlineData']['data']))
        print('Saved to output.png')
    elif 'text' in part:
        print(part['text'])
"
```

### Image-to-Image (curl)

```bash
# Base64-encode the input image
INPUT_B64=$(base64 -w0 input_garment.jpg)

curl -s -X POST \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent" \
  -H "x-goog-api-key: $GOOGLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{
      "parts": [
        {
          "inlineData": {
            "mimeType": "image/jpeg",
            "data": "'"$INPUT_B64"'"
          }
        },
        {
          "text": "Transform this garment photo into a professional fashion editorial. Place the garment on a model in a studio setting with soft directional lighting. Maintain exact garment details - fabric, color, construction, buttons, stitching."
        }
      ]
    }],
    "generationConfig": {
      "responseModalities": ["TEXT", "IMAGE"]
    }
  }' | python3 -c "
import json, sys, base64
resp = json.load(sys.stdin)
for part in resp['candidates'][0]['content']['parts']:
    if 'inlineData' in part:
        with open('output_editorial.png', 'wb') as f:
            f.write(base64.b64decode(part['inlineData']['data']))
        print('Saved to output_editorial.png')
"
```

### Text-to-Image with Aspect Ratio (Python)

```python
from google import genai
from google.genai import types
import base64

client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

response = client.models.generate_content(
    model="gemini-2.5-flash-image",
    contents="A fashion model wearing an elegant white blazer, editorial photography, soft studio lighting",
    config=types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"],
        # Aspect ratio is inferred from the prompt or can be guided
        # by describing the composition
    )
)

# Save the generated image
for part in response.candidates[0].content.parts:
    if hasattr(part, 'inline_data') and part.inline_data:
        with open("output.png", "wb") as f:
            f.write(base64.b64decode(part.inline_data.data))
```

---

## Fashion Editorial Prompt Recipes

### Recipe 1: Chrome Mannequin Product Shot

```
Professional product photography of [GARMENT DESCRIPTION] displayed on a polished
chrome mannequin torso. Seamless pure white background. Three-point studio lighting:
key light at 45 degrees camera-right, fill light camera-left at half intensity,
rim light from behind to separate from background. Sharp focus on fabric texture.
Clean e-commerce aesthetic. 4:5 aspect ratio.
```

### Recipe 2: Editorial Fashion Portrait

```
High-end editorial fashion photograph. A model with [FEATURES] wearing
[GARMENT DESCRIPTION]. Shot on medium format camera with shallow depth of field.
Soft window light from the left side creating gentle shadows on the face.
Neutral gray backdrop. The garment is the hero element. Vogue editorial style.
Professional retouching, clean skin, natural makeup. 2:3 aspect ratio.
```

### Recipe 3: Lifestyle Campaign

```
Aspirational lifestyle fashion campaign image. A [PERSON DESCRIPTION] wearing
[GARMENT DESCRIPTION] in [SETTING]. Golden hour natural light, warm color palette.
Candid moment, authentic expression. The outfit is styled casually but intentionally.
Background slightly out of focus. Shot with a 85mm lens. Campaign photography for
a premium contemporary brand. 16:9 aspect ratio.
```

### Recipe 4: Flat Lay Product

```
Perfectly styled flat lay photograph of [GARMENT DESCRIPTION] arranged on a clean
marble surface. The garment is neatly folded/arranged to show construction details.
Accompanied by minimal styling props: a leather watch, sunglasses, a small potted
plant. Overhead shot, even diffused lighting, no harsh shadows. E-commerce catalog
style. 1:1 aspect ratio.
```

### Recipe 5: Campaign with Text Overlay (Nano Banana Pro)

**Use `gemini-3-pro-image-preview` for reliable text rendering.**

```
Fashion advertising campaign poster. A model wearing [GARMENT DESCRIPTION] against
a [BACKGROUND]. Professional studio lighting. In the upper portion of the image,
display the text "[BRAND NAME]" in elegant serif typography, white color.
Below the model, smaller text reads "[TAGLINE]". The text should be crisp, legible,
and professionally typeset. Magazine advertisement aesthetic. 4:5 aspect ratio.
```

### Recipe 6: Garment Detail / Texture Close-Up

```
Extreme close-up photograph of [FABRIC TYPE] fabric texture. Macro lens perspective
showing individual thread weave, fiber structure, and material quality. Soft raking
light from the side to emphasize texture depth. Shallow depth of field with the
center in sharp focus. Color accurate to [COLOR DESCRIPTION]. Product photography
for luxury fashion brand. 1:1 aspect ratio.
```

### Recipe 7: Color Variant Generation (Image-to-Image)

Send the original garment image with this prompt:
```
Change the color of this garment to [TARGET COLOR] while preserving every other
detail exactly: same fabric texture, same construction, same drape, same buttons
and hardware, same fit. Only the color changes. Maintain the exact same lighting,
angle, and background.
```

### Recipe 8: Background Swap (Image-to-Image)

Send the fashion photo with this prompt:
```
Replace the background with [NEW BACKGROUND DESCRIPTION]. Keep the model, garment,
pose, and lighting on the subject exactly the same. Naturally blend the subject
into the new environment with appropriate ambient lighting adjustments.
```

---

## Multi-Turn Refinement

Nano Banana supports multi-turn conversations for iterative editing:

```python
# Turn 1: Generate base image
response1 = client.models.generate_content(
    model="gemini-2.5-flash-image",
    contents="Fashion model in white blazer, studio portrait"
)

# Turn 2: Refine the image (send previous image back)
response2 = client.models.generate_content(
    model="gemini-2.5-flash-image",
    contents=[
        previous_image_part,  # From response1
        "Make the lighting warmer and add a slight golden tone. Soften the background more."
    ]
)

# Turn 3: Further refinement
response3 = client.models.generate_content(
    model="gemini-2.5-flash-image",
    contents=[
        refined_image_part,  # From response2
        "Add a subtle lens flare from the upper right corner."
    ]
)
```

---

## Best Practices for Fashion Photography

1. **Be specific about lighting**: Name light sources (softbox, window, rim light) rather than describing brightness
2. **Describe lens and perspective**: "85mm lens, f/2.8, eye-level" gives better results than "close-up"
3. **Mention materials explicitly**: "raw silk" not just "silk"; "matte cotton twill" not just "cotton"
4. **Reference photography styles**: "Vogue editorial", "campaign photography", "lookbook style"
5. **Control composition**: Describe foreground, mid-ground, background placement
6. **Color accuracy**: Use specific color names like "dusty rose" or "charcoal heather" not just "pink" or "gray"
7. **For text overlays**: Always use Nano Banana Pro (`gemini-3-pro-image-preview`)
8. **For speed/iteration**: Use standard Nano Banana (`gemini-2.5-flash-image`)
9. **Up to 14 reference images**: Use multiple reference angles for better garment preservation
10. **Aspect ratio in prompt**: Describe the composition to imply aspect ratio if not directly settable

---

## Pricing Reference

| Model | Cost per Image | Monthly Budget (1000 images) |
|-------|---------------|------------------------------|
| Nano Banana | ~$0.039 | ~$39 |
| Nano Banana Pro | ~$0.06-0.10 (estimated) | ~$60-100 |

---

## References

- [Gemini Image Generation API](https://ai.google.dev/gemini-api/docs/image-generation)
- [Gemini 2.5 Flash Image Docs](https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash-image)
- [Gemini 2.5 Flash Image Announcement](https://developers.googleblog.com/introducing-gemini-2-5-flash-image/)
- [Production Release with Aspect Ratios](https://developers.googleblog.com/en/gemini-2-5-flash-image-now-ready-for-production-with-new-aspect-ratios/)
- [Nano Banana Pro API](https://kie.ai/nano-banana)
