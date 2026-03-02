"""VFX Object Tracking Pipeline v2.

Generates a 3D model from a screenshot (Hunyuan3D via ComfyUI), imports it
into Blender, tracks it against video footage using GeoTracker, and composites
the result.

Based on the official KeenTools tutorial workflow:
    1. Generate 3D model from screenshot (Hunyuan3D v2 or pre-made GLB)
    2. Import GLB into Blender, fix rotation/parents (tutorial-critical)
    3. Configure GeoTracker, analyze clip, align model
    4. Track with pins, refine, bake animation
    5. Composite tracked mesh over video, render frames

Usage:
    python -m vfx_pipeline \\
        --video footage.mp4 \\
        --screenshot object.png \\
        --output /tmp/vfx_out

    # With pre-made GLB (skip generation):
    python -m vfx_pipeline \\
        --video footage.mp4 \\
        --glb model.glb \\
        --output /tmp/vfx_out

    # Using KeenTools example files:
    python -m vfx_pipeline \\
        --video assets/keentools-example/ComfyUI+GeoTracker_example/5835604-hd_1920_1080_25fps.mp4 \\
        --glb assets/keentools-example/ComfyUI+GeoTracker_example/Car.glb \\
        --output /tmp/vfx_test
"""

import argparse
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .blender_client import BlenderClient
from .blender_scripts import (
    ANALYZE_CLIP,
    CHECK_SCENE_STATE,
    ENTER_PINMODE_AND_ALIGN,
    IMPORT_AND_PREPARE_GLB,
    LOAD_FOOTAGE,
    RENDER_ANIMATION,
    RESET_AND_CREATE_GEOTRACKER,
    SAVE_BLEND,
    SETUP_COMPOSITOR,
    SETUP_GEOTRACKER,
    TRACK_AND_REFINE,
)
from .comfyui_client import ComfyUIClient
from .validators import (
    validate_composite_output,
    validate_glb,
    validate_scene_setup,
    validate_tracking,
)
from .workflows import (
    build_hunyuan3d_generation,
    load_reference_workflow,
    patch_workflow_image,
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class StepResult:
    ok: bool
    message: str
    data: dict = field(default_factory=dict)
    duration_seconds: float = 0.0


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


class VFXPipeline:
    """Orchestrates the full Hunyuan3D → GeoTracker → Compositing pipeline."""

    def __init__(
        self,
        comfyui_url: str = "http://comfyui:8188",
        blender_url: str = "ws://127.0.0.1:8765",
    ):
        self.comfy = ComfyUIClient(comfyui_url)
        self.blender_url = blender_url
        self.output_dir: Optional[Path] = None

    def _ensure_output_dir(self, output_path: str) -> Path:
        p = Path(output_path)
        p.mkdir(parents=True, exist_ok=True)
        self.output_dir = p
        return p

    # ------------------------------------------------------------------
    # Step 1: 3D Model Generation (ComfyUI + Hunyuan3D v2)
    # ------------------------------------------------------------------

    def step1_generate_3d(
        self,
        screenshot_path: str,
        seed: int = 42,
        reference_workflow: Optional[str] = None,
    ) -> StepResult:
        """Generate a textured 3D GLB from a single screenshot.

        Uses the KeenTools example Hunyuan3D workflow if reference_workflow
        is provided, otherwise builds the workflow programmatically.
        """
        t0 = time.time()
        print(f"\n{'='*60}")
        print("  Step 1: 3D Model Generation (Hunyuan3D v2)")
        print(f"{'='*60}")

        # Upload screenshot to ComfyUI
        filename = Path(screenshot_path).name
        if not screenshot_path.startswith("/root/ComfyUI"):
            print(f"  Uploading {filename}...")
            filename = self.comfy.upload_image(screenshot_path)

        # Build or load workflow
        if reference_workflow and Path(reference_workflow).exists():
            print(f"  Using reference workflow: {reference_workflow}")
            workflow = load_reference_workflow(reference_workflow)
            workflow = patch_workflow_image(workflow, filename)
        else:
            print("  Building Hunyuan3D v2 workflow...")
            workflow = build_hunyuan3d_generation(filename, seed=seed)

        # Run workflow
        print("  Running 3D generation (this may take 2-5 minutes)...")
        outputs = self.comfy.run_workflow(workflow, timeout=600)

        # Extract GLB paths
        textured_glb = self.comfy.get_output_path(outputs, "70")
        untextured_glb = self.comfy.get_output_path(outputs, "24")

        # Use textured if available, fall back to untextured
        glb_path = textured_glb or untextured_glb
        if not glb_path:
            # Try all nodes for any GLB output
            for node_id in outputs:
                p = self.comfy.get_output_path(outputs, node_id)
                if p and (p.endswith(".glb") or p.endswith(".gltf")):
                    glb_path = p
                    break

        # Validate
        if glb_path:
            ok, msg = validate_glb(glb_path)
        else:
            ok, msg = False, "No GLB output found in workflow results"

        duration = time.time() - t0
        print(f"  {'OK' if ok else 'FAIL'}: {msg}")
        print(f"  Duration: {duration:.1f}s")

        return StepResult(
            ok=ok,
            message=msg,
            data={
                "glb_path": glb_path,
                "textured_glb": textured_glb,
                "untextured_glb": untextured_glb,
            },
            duration_seconds=duration,
        )

    # ------------------------------------------------------------------
    # Step 2: Blender Scene Setup
    # ------------------------------------------------------------------

    def step2_setup_scene(
        self,
        glb_path: str,
        video_path: str,
        mesh_name: str = "tracked_object",
    ) -> StepResult:
        """Import GLB and video into Blender, configure GeoTracker.

        Critical fixes from tutorial (missing in v1):
        - Convert rotation mode QUATERNION → XYZ Euler
        - Clear parent relationships
        - Delete orphan empties
        - Rename mesh
        - Analyze clip
        """
        t0 = time.time()
        print(f"\n{'='*60}")
        print("  Step 2: Blender Scene Setup")
        print(f"{'='*60}")

        # Free ComfyUI GPU memory before Blender work
        print("  Freeing ComfyUI GPU memory...")
        try:
            self.comfy.free_memory()
        except Exception:
            pass
        time.sleep(2)

        results = {}

        with BlenderClient(self.blender_url) as blender:
            # 2a. Reset scene and create GeoTracker
            print("  Resetting Blender scene...")
            r = blender.execute_python(RESET_AND_CREATE_GEOTRACKER)
            results["reset"] = r
            ok, msg = validate_scene_setup(str(r))
            if not ok:
                return StepResult(False, msg, results, time.time() - t0)

            # 2b. Load video footage
            print(f"  Loading footage: {video_path}")
            r = blender.execute_python(LOAD_FOOTAGE.format(video_path=video_path))
            results["footage"] = r

            # 2c. Import and prepare GLB (the critical tutorial fix)
            print(f"  Importing GLB: {glb_path}")
            print("    - Converting rotation: QUATERNION → XYZ Euler")
            print("    - Clearing parent relationships")
            print("    - Deleting orphan empties")
            print(f"    - Renaming mesh to '{mesh_name}'")
            r = blender.execute_python(
                IMPORT_AND_PREPARE_GLB.format(glb_path=glb_path, mesh_name=mesh_name)
            )
            results["import"] = r
            ok, msg = validate_scene_setup(str(r))
            if not ok:
                return StepResult(False, f"GLB import failed: {msg}", results, time.time() - t0)

            # 2d. Configure GeoTracker
            print("  Configuring GeoTracker...")
            r = blender.execute_python(SETUP_GEOTRACKER.format(mesh_name=mesh_name))
            results["geotracker"] = r

            # 2e. Analyze clip (new in v2 — v1 skipped this)
            print("  Analyzing clip for optical flow...")
            r = blender.execute_python(ANALYZE_CLIP, timeout=300)
            results["analyze"] = r

            # 2f. Validate scene state
            print("  Validating scene...")
            r = blender.execute_python(CHECK_SCENE_STATE)
            results["state"] = r

        duration = time.time() - t0
        print(f"  Scene setup complete ({duration:.1f}s)")

        return StepResult(
            ok=True,
            message=f"Scene ready: {mesh_name} + GeoTracker configured",
            data=results,
            duration_seconds=duration,
        )

    # ------------------------------------------------------------------
    # Step 3: GeoTracker Tracking
    # ------------------------------------------------------------------

    def step3_track(
        self,
        pin_frames: Optional[list[int]] = None,
        initial_transform: Optional[dict] = None,
        timeout: int = 600,
    ) -> StepResult:
        """Run GeoTracker tracking with multi-keyframe pins.

        Args:
            pin_frames: Frame numbers for pin positions. If None, auto-spaces 5 pins.
            initial_transform: {location: [x,y,z], rotation: [x,y,z], scale: [x,y,z]}
            timeout: Max seconds for tracking to complete.
        """
        t0 = time.time()
        print(f"\n{'='*60}")
        print("  Step 3: GeoTracker Tracking")
        print(f"{'='*60}")

        results = {}

        # Determine initial alignment method
        use_magic = initial_transform is None
        loc = initial_transform.get("location", [0, 0, 0]) if initial_transform else [0, 0, 0]
        rot = initial_transform.get("rotation", [0, 0, 0]) if initial_transform else [0, 0, 0]
        scale = initial_transform.get("scale", [1, 1, 1]) if initial_transform else [1, 1, 1]

        if pin_frames is None:
            pin_frames = []  # Will auto-detect in tracking script

        with BlenderClient(self.blender_url) as blender:
            # 3a. Enter pin mode and align
            align_method = "magic keyframe" if use_magic else "manual transform"
            print(f"  Aligning model ({align_method})...")
            r = blender.execute_python(
                ENTER_PINMODE_AND_ALIGN.format(
                    location=list(loc),
                    rotation=list(rot),
                    scale=list(scale),
                    use_magic="True" if use_magic else "False",
                ),
                timeout=60,
            )
            results["align"] = r

            # 3b. Track and refine
            print(f"  Tracking (timeout: {timeout}s)...")
            r = blender.execute_python(
                TRACK_AND_REFINE.format(
                    pin_frames_json=json.dumps(pin_frames),
                    timeout_seconds=timeout,
                ),
                timeout=timeout + 120,  # Extra buffer for bake/export
            )
            results["tracking"] = r

            # 3c. Validate tracking
            ok, msg = validate_tracking(str(r))
            if not ok:
                print(f"  WARNING: {msg}")
                # Don't fail — partial tracking may still be usable

            # 3d. Save blend file
            if self.output_dir:
                blend_path = str(self.output_dir / "tracked_scene.blend")
                print(f"  Saving: {blend_path}")
                blender.execute_python(SAVE_BLEND.format(output_path=blend_path))
                results["blend_path"] = blend_path

        duration = time.time() - t0
        print(f"  Tracking complete ({duration:.1f}s)")

        return StepResult(
            ok=ok,
            message=msg,
            data=results,
            duration_seconds=duration,
        )

    # ------------------------------------------------------------------
    # Step 4: Compositing & Render
    # ------------------------------------------------------------------

    def step4_composite(
        self,
        video_path: str,
        render_engine: str = "BLENDER_EEVEE",
    ) -> StepResult:
        """Set up compositor and render tracked mesh over video."""
        t0 = time.time()
        print(f"\n{'='*60}")
        print("  Step 4: Compositing & Render")
        print(f"{'='*60}")

        output_path = str(self.output_dir) if self.output_dir else "/tmp/vfx_output"
        results = {}

        with BlenderClient(self.blender_url) as blender:
            # 4a. Setup compositor
            print(f"  Setting up compositor ({render_engine})...")
            r = blender.execute_python(
                SETUP_COMPOSITOR.format(
                    video_path=video_path,
                    output_path=output_path,
                    render_engine=render_engine,
                )
            )
            results["compositor"] = r

            # 4b. Render animation
            print("  Rendering (this may take a while)...")
            r = blender.execute_python(RENDER_ANIMATION, timeout=3600)
            results["render"] = r

        # 4c. Validate output
        ok, msg = validate_composite_output(output_path)

        duration = time.time() - t0
        print(f"  {'OK' if ok else 'FAIL'}: {msg}")
        print(f"  Duration: {duration:.1f}s")

        return StepResult(
            ok=ok,
            message=msg,
            data={"output_path": output_path, **results},
            duration_seconds=duration,
        )

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    def run(
        self,
        video_path: str,
        output_path: str = "/tmp/vfx_output",
        screenshot_path: Optional[str] = None,
        glb_path: Optional[str] = None,
        mesh_name: str = "tracked_object",
        seed: int = 42,
        reference_workflow: Optional[str] = None,
        pin_frames: Optional[list[int]] = None,
        initial_transform: Optional[dict] = None,
        render_engine: str = "BLENDER_EEVEE",
        tracking_timeout: int = 600,
        skip_to: Optional[int] = None,
    ) -> dict:
        """Run the full pipeline end-to-end.

        Args:
            video_path: Path to input video.
            output_path: Directory for all outputs.
            screenshot_path: Screenshot for 3D generation (required if no glb_path).
            glb_path: Pre-made GLB file (skip step 1).
            mesh_name: Name for the tracked mesh in Blender.
            seed: Random seed for Hunyuan3D.
            reference_workflow: Path to KeenTools example ComfyUI workflow JSON.
            pin_frames: Frame numbers for GeoTracker pins.
            initial_transform: Initial model alignment transform.
            render_engine: "BLENDER_EEVEE" or "CYCLES".
            tracking_timeout: Max seconds for GeoTracker.
            skip_to: Skip to step N (2=scene, 3=track, 4=composite).
        """
        out = self._ensure_output_dir(output_path)
        results = {}
        total_t0 = time.time()

        print("\n" + "=" * 60)
        print("  VFX Object Tracking Pipeline v2")
        print(f"  Video:      {video_path}")
        if screenshot_path:
            print(f"  Screenshot: {screenshot_path}")
        if glb_path:
            print(f"  GLB:        {glb_path}")
        print(f"  Output:     {output_path}")
        print(f"  Mesh name:  {mesh_name}")
        print("=" * 60)

        # Step 1: Generate 3D model (or use provided GLB)
        if not glb_path and (not skip_to or skip_to <= 1):
            if not screenshot_path:
                raise ValueError("Either --screenshot or --glb is required")
            result = self.step1_generate_3d(screenshot_path, seed, reference_workflow)
            results["step1"] = result
            if not result.ok:
                raise RuntimeError(f"Step 1 failed: {result.message}")
            glb_path = result.data.get("glb_path")

        if not glb_path:
            raise ValueError("No GLB available. Provide --screenshot or --glb.")

        # Validate GLB before proceeding
        ok, msg = validate_glb(glb_path)
        if not ok:
            raise ValueError(f"Invalid GLB: {msg}")
        print(f"\n  GLB validated: {msg}")

        # Step 2: Scene setup
        if not skip_to or skip_to <= 2:
            result = self.step2_setup_scene(glb_path, video_path, mesh_name)
            results["step2"] = result
            if not result.ok:
                raise RuntimeError(f"Step 2 failed: {result.message}")

        # Step 3: Tracking
        if not skip_to or skip_to <= 3:
            result = self.step3_track(pin_frames, initial_transform, tracking_timeout)
            results["step3"] = result
            # Don't fail on partial tracking — compositor can still render

        # Step 4: Compositing
        if not skip_to or skip_to <= 4:
            result = self.step4_composite(video_path, render_engine)
            results["step4"] = result

        total_duration = time.time() - total_t0

        print("\n" + "=" * 60)
        print("  Pipeline complete!")
        print(f"  Total duration: {total_duration:.1f}s")
        print(f"  Output: {output_path}")
        print("=" * 60)

        # Save metadata
        meta = {
            "video": video_path,
            "screenshot": screenshot_path,
            "glb": glb_path,
            "mesh_name": mesh_name,
            "seed": seed,
            "render_engine": render_engine,
            "total_duration_seconds": total_duration,
            "steps": {
                name: {"ok": r.ok, "message": r.message, "duration": r.duration_seconds}
                for name, r in results.items()
            },
        }
        meta_path = out / "pipeline_metadata.json"
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)
        print(f"  Metadata: {meta_path}")

        return results


def main():
    parser = argparse.ArgumentParser(
        description="VFX Object Tracking Pipeline v2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate 3D from screenshot + track:
  %(prog)s --video footage.mp4 --screenshot car.png --output /tmp/vfx

  # Use pre-made GLB (skip 3D generation):
  %(prog)s --video footage.mp4 --glb model.glb --output /tmp/vfx

  # KeenTools example files:
  %(prog)s --video assets/keentools-example/.../5835604-hd_1920_1080_25fps.mp4 \\
           --glb assets/keentools-example/.../Car.glb --output /tmp/vfx_test
        """,
    )
    parser.add_argument("--video", required=True, help="Input video path")
    parser.add_argument("--screenshot", help="Screenshot for 3D generation")
    parser.add_argument("--glb", help="Pre-made GLB model (skip step 1)")
    parser.add_argument("--output", default="/tmp/vfx_output", help="Output directory")
    parser.add_argument("--name", default="tracked_object", help="Mesh name in Blender")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--reference-workflow", help="KeenTools example workflow JSON path")
    parser.add_argument(
        "--pin-frames",
        help="Comma-separated frame numbers for GeoTracker pins (e.g., 1,50,100)",
    )
    parser.add_argument(
        "--initial-transform",
        help='JSON transform: \'{"location":[0,0,0],"rotation":[0,0,0],"scale":[1,1,1]}\'',
    )
    parser.add_argument(
        "--render-engine",
        choices=["BLENDER_EEVEE", "CYCLES"],
        default="BLENDER_EEVEE",
        help="Blender render engine",
    )
    parser.add_argument("--timeout", type=int, default=600, help="Tracking timeout (seconds)")
    parser.add_argument("--skip-to", type=int, choices=[1, 2, 3, 4], help="Skip to step N")
    parser.add_argument("--comfyui-url", default="http://comfyui:8188")
    parser.add_argument("--blender-url", default="ws://127.0.0.1:8765")

    args = parser.parse_args()

    # Parse pin frames
    pin_frames = None
    if args.pin_frames:
        pin_frames = [int(f.strip()) for f in args.pin_frames.split(",")]

    # Parse initial transform
    initial_transform = None
    if args.initial_transform:
        initial_transform = json.loads(args.initial_transform)

    pipeline = VFXPipeline(args.comfyui_url, args.blender_url)
    pipeline.run(
        video_path=args.video,
        output_path=args.output,
        screenshot_path=args.screenshot,
        glb_path=args.glb,
        mesh_name=args.name,
        seed=args.seed,
        reference_workflow=args.reference_workflow,
        pin_frames=pin_frames,
        initial_transform=initial_transform,
        render_engine=args.render_engine,
        tracking_timeout=args.timeout,
        skip_to=args.skip_to,
    )


if __name__ == "__main__":
    main()
