#!/usr/bin/env python3
"""Poll Veo operations and download completed videos."""
import json, urllib.request, time, base64, os, sys

API_KEY = "AIzaSyBGC0OnF9bGOcAgtebKHf79TBJQhpHWTKY"
OUTPUT_DIR = "assets/animated"
os.makedirs(OUTPUT_DIR, exist_ok=True)

with open('scripts/veo-operations.json') as f:
    ops = json.load(f)

# Also check the test operation
test_op = {"id": "test", "operation": "models/veo-3.0-generate-001/operations/iry54f0llav2", "aspect": "16:9", "output": "veo_test.mp4"}

all_ops = ops  # skip test
completed = set()
max_polls = 30  # 30 polls * 30s = 15 minutes max
poll = 0

while poll < max_polls and len(completed) < len(all_ops):
    poll += 1
    print(f"\n--- Poll {poll}/{max_polls} (completed: {len(completed)}/{len(all_ops)}) ---")
    
    for op in all_ops:
        if op['id'] in completed:
            continue
        url = f"https://generativelanguage.googleapis.com/v1beta/{op['operation']}?key={API_KEY}"
        try:
            resp = urllib.request.urlopen(url, timeout=15)
            result = json.loads(resp.read())
            done = result.get('done', False)
            
            if done:
                resp_data = result.get('response', {})
                samples = resp_data.get('generateVideoResponse', {}).get('generatedSamples', [])
                if samples:
                    video_data = samples[0].get('video', {})
                    video_uri = video_data.get('uri', '')
                    
                    if video_uri:
                        # Download video
                        out_path = os.path.join(OUTPUT_DIR, op['output'])
                        vid_resp = urllib.request.urlopen(f"{video_uri}&key={API_KEY}", timeout=120)
                        with open(out_path, 'wb') as vf:
                            vf.write(vid_resp.read())
                        size = os.path.getsize(out_path)
                        print(f"  DOWNLOADED {op['id']}: {out_path} ({size:,} bytes)")
                        completed.add(op['id'])
                    else:
                        # Check for inline base64
                        b64 = video_data.get('bytesBase64Encoded', '')
                        if b64:
                            out_path = os.path.join(OUTPUT_DIR, op['output'])
                            with open(out_path, 'wb') as vf:
                                vf.write(base64.b64decode(b64))
                            size = os.path.getsize(out_path)
                            print(f"  DOWNLOADED {op['id']} (base64): {out_path} ({size:,} bytes)")
                            completed.add(op['id'])
                        else:
                            print(f"  {op['id']}: done but no video URI or data")
                            completed.add(op['id'])
                elif 'error' in result:
                    print(f"  {op['id']}: ERROR - {result['error'].get('message', 'unknown')}")
                    completed.add(op['id'])
                else:
                    print(f"  {op['id']}: done but no samples")
                    completed.add(op['id'])
            else:
                meta = result.get('metadata', {})
                state = meta.get('state', 'unknown') if isinstance(meta, dict) else 'unknown'
                print(f"  {op['id']}: in progress (state={state})")
        except Exception as e:
            print(f"  {op['id']}: poll error - {e}")
    
    if len(completed) < len(all_ops):
        time.sleep(30)

print(f"\n=== FINAL: {len(completed)}/{len(all_ops)} completed ===")
for op in all_ops:
    out_path = os.path.join(OUTPUT_DIR, op['output'])
    if os.path.exists(out_path):
        size = os.path.getsize(out_path)
        print(f"  {op['id']}: {out_path} ({size:,} bytes)")
    else:
        print(f"  {op['id']}: NOT DOWNLOADED")
