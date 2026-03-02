"""Tests for VFX Object Tracking Pipeline v2.

Tests are organized by pipeline component:
    1. Validators (pure functions, no external deps)
    2. Workflow builders (pure functions)
    3. Blender scripts (string template validation)
    4. Pipeline orchestration (mocked clients)
    5. Integration test with KeenTools example files (validates structure)
"""

import json
import os
import struct
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import sys

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from vfx_pipeline.validators import (
    validate_glb,
    validate_scene_setup,
    validate_tracking,
    validate_composite_output,
)
from vfx_pipeline.workflows import (
    build_hunyuan3d_generation,
    load_reference_workflow,
    patch_workflow_image,
)
from vfx_pipeline.blender_scripts import (
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
from vfx_pipeline.pipeline import VFXPipeline, StepResult


# =====================================================================
# Fixtures
# =====================================================================


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def valid_glb(tmp_dir):
    """Create a minimal valid GLB file (glTF binary header)."""
    path = tmp_dir / "test.glb"
    with open(path, "wb") as f:
        # glTF header: magic + version + length
        f.write(b"glTF")  # magic
        f.write(struct.pack("<I", 2))  # version 2
        f.write(struct.pack("<I", 1000))  # total length
        f.write(b"\x00" * 988)  # padding to 1000 bytes
    return str(path)


@pytest.fixture
def invalid_glb(tmp_dir):
    """Create a file with wrong magic bytes."""
    path = tmp_dir / "bad.glb"
    with open(path, "wb") as f:
        f.write(b"NOT_GLTF" + b"\x00" * 100)
    return str(path)


@pytest.fixture
def empty_file(tmp_dir):
    """Create an empty file."""
    path = tmp_dir / "empty.glb"
    path.touch()
    return str(path)


@pytest.fixture
def composited_frames(tmp_dir):
    """Create mock composited PNG frames."""
    for i in range(1, 11):
        path = tmp_dir / f"composited_{i:04d}.png"
        with open(path, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n")  # Valid PNG header
            f.write(b"\x00" * 100)
    return str(tmp_dir)


@pytest.fixture
def keentools_example_dir():
    """Path to KeenTools example files (if downloaded)."""
    base = Path(__file__).parent.parent / "assets" / "keentools-example" / "ComfyUI+GeoTracker_example"
    if base.exists():
        return base
    pytest.skip("KeenTools example files not downloaded")


# =====================================================================
# 1. Validator Tests
# =====================================================================


class TestValidateGLB:
    def test_valid_glb(self, valid_glb):
        ok, msg = validate_glb(valid_glb)
        assert ok is True
        assert "Valid GLB" in msg
        assert "glTF v2" in msg

    def test_empty_path(self):
        ok, msg = validate_glb("")
        assert ok is False
        assert "empty" in msg.lower()

    def test_missing_file(self):
        ok, msg = validate_glb("/nonexistent/path.glb")
        assert ok is False
        assert "not found" in msg.lower()

    def test_empty_file(self, empty_file):
        ok, msg = validate_glb(empty_file)
        assert ok is False
        assert "too small" in msg.lower()

    def test_invalid_magic(self, invalid_glb):
        ok, msg = validate_glb(invalid_glb)
        assert ok is False
        assert "Invalid GLB magic" in msg

    def test_wrong_version(self, tmp_dir):
        path = tmp_dir / "v1.glb"
        with open(path, "wb") as f:
            f.write(b"glTF")
            f.write(struct.pack("<I", 1))  # version 1
            f.write(struct.pack("<I", 100))
            f.write(b"\x00" * 88)
        ok, msg = validate_glb(str(path))
        assert ok is False
        assert "version" in msg.lower()


class TestValidateSceneSetup:
    def test_success_with_result(self):
        ok, msg = validate_scene_setup("Some output\nRESULT:status=ready,gt_index=0")
        assert ok is True
        assert "ready" in msg

    def test_error_in_output(self):
        ok, msg = validate_scene_setup("ERROR: KeenTools addon not available")
        assert ok is False
        assert "KeenTools" in msg

    def test_empty_result(self):
        ok, msg = validate_scene_setup("")
        assert ok is False

    def test_no_result_line(self):
        ok, msg = validate_scene_setup("Just some output without RESULT")
        assert ok is True  # Passes without structured result


class TestValidateTracking:
    def test_good_tracking(self):
        ok, msg = validate_tracking("RESULT:status=tracked,keyframes=150,total_frames=200")
        assert ok is True
        assert "150" in msg

    def test_too_few_keyframes(self):
        ok, msg = validate_tracking("RESULT:status=tracked,keyframes=1,total_frames=200")
        assert ok is False
        assert "Too few" in msg

    def test_custom_min_keyframes(self):
        ok, msg = validate_tracking(
            "RESULT:status=tracked,keyframes=5,total_frames=200",
            min_keyframes=10,
        )
        assert ok is False

    def test_tracking_error(self):
        ok, msg = validate_tracking("ERROR: No 3D viewport found")
        assert ok is False


class TestValidateCompositeOutput:
    def test_valid_frames(self, composited_frames):
        ok, msg = validate_composite_output(composited_frames)
        assert ok is True
        assert "10 frames" in msg

    def test_missing_directory(self):
        ok, msg = validate_composite_output("/nonexistent/path")
        assert ok is False
        assert "not found" in msg.lower()

    def test_empty_directory(self, tmp_dir):
        ok, msg = validate_composite_output(str(tmp_dir))
        assert ok is False
        assert "No composited" in msg

    def test_missing_frames_warning(self, tmp_dir):
        # Create only 5 frames when 100 expected
        for i in range(1, 6):
            path = tmp_dir / f"composited_{i:04d}.png"
            with open(path, "wb") as f:
                f.write(b"\x89PNG\r\n\x1a\n\x00" * 10)
        ok, msg = validate_composite_output(str(tmp_dir), expected_frames=100)
        assert ok is False
        assert "Missing" in msg


# =====================================================================
# 2. Workflow Builder Tests
# =====================================================================


class TestBuildHunyuan3dGeneration:
    def test_returns_dict(self):
        wf = build_hunyuan3d_generation("test.png")
        assert isinstance(wf, dict)

    def test_has_required_nodes(self):
        wf = build_hunyuan3d_generation("test.png")
        # Must have: LoadImage, model loader, mesh gen, VAE decode, export
        class_types = {v["class_type"] for v in wf.values()}
        assert "LoadImage" in class_types
        assert "Hy3DModelLoader" in class_types
        assert "Hy3DGenerateMesh" in class_types
        assert "Hy3DVAEDecode" in class_types
        assert "Hy3DExportMesh" in class_types

    def test_image_filename_set(self):
        wf = build_hunyuan3d_generation("my_car.png")
        load_node = wf["10"]
        assert load_node["inputs"]["image"] == "my_car.png"

    def test_seed_propagation(self):
        wf = build_hunyuan3d_generation("test.png", seed=123)
        gen_node = wf["21"]
        assert gen_node["inputs"]["seed"] == 123

    def test_has_texture_pipeline(self):
        wf = build_hunyuan3d_generation("test.png")
        class_types = {v["class_type"] for v in wf.values()}
        assert "Hy3DDelightImage" in class_types
        assert "Hy3DSampleMultiView" in class_types
        assert "Hy3DBakeFromMultiview" in class_types
        assert "Hy3DApplyTexture" in class_types

    def test_has_background_removal(self):
        wf = build_hunyuan3d_generation("test.png")
        class_types = {v["class_type"] for v in wf.values()}
        assert "TransparentBGSession+" in class_types
        assert "ImageRemoveBackground+" in class_types

    def test_two_export_nodes(self):
        """Must export both untextured (node 24) and textured (node 70) GLB."""
        wf = build_hunyuan3d_generation("test.png")
        exports = [k for k, v in wf.items() if v["class_type"] == "Hy3DExportMesh"]
        assert len(exports) == 2
        assert "24" in exports  # untextured
        assert "70" in exports  # textured


class TestLoadReferenceWorkflow:
    def test_loads_json(self, tmp_dir):
        wf_path = tmp_dir / "test.json"
        wf_path.write_text('{"nodes": [], "links": []}')
        result = load_reference_workflow(str(wf_path))
        assert "nodes" in result

    def test_loads_keentools_example(self, keentools_example_dir):
        wf_path = keentools_example_dir / "3dmodelgeneration.json"
        result = load_reference_workflow(str(wf_path))
        assert "nodes" in result
        assert "links" in result
        # Verify it's Hunyuan3D workflow
        node_types = {n["type"] for n in result["nodes"]}
        assert "Hy3DModelLoader" in node_types
        assert "Hy3DExportMesh" in node_types


class TestPatchWorkflowImage:
    def test_patches_ui_format(self):
        wf = {
            "last_node_id": 1,
            "nodes": [
                {"type": "LoadImage", "widgets_values": ["original.png", "image"]},
            ],
        }
        patched = patch_workflow_image(wf, "new_image.png")
        assert patched["nodes"][0]["widgets_values"][0] == "new_image.png"

    def test_patches_api_format(self):
        wf = {
            "1": {"class_type": "LoadImage", "inputs": {"image": "original.png"}},
        }
        patched = patch_workflow_image(wf, "new_image.png")
        assert patched["1"]["inputs"]["image"] == "new_image.png"


# =====================================================================
# 3. Blender Script Tests
# =====================================================================


class TestBlenderScripts:
    """Validate Blender script templates are well-formed."""

    def test_reset_script_has_keentools_enable(self):
        assert "addon_enable" in RESET_AND_CREATE_GEOTRACKER
        assert "keentools" in RESET_AND_CREATE_GEOTRACKER
        assert "create_geotracker" in RESET_AND_CREATE_GEOTRACKER

    def test_load_footage_accepts_path(self):
        script = LOAD_FOOTAGE.format(video_path="/tmp/test.mp4")
        assert "/tmp/test.mp4" in script
        assert "movieclips.load" in script

    def test_import_glb_has_tutorial_fixes(self):
        """The critical v2 fix: rotation mode, parent clearing, empty deletion."""
        script = IMPORT_AND_PREPARE_GLB.format(glb_path="/tmp/test.glb", mesh_name="car")
        # Must convert rotation mode
        assert "QUATERNION" in script
        assert "XYZ" in script
        assert "rotation_mode" in script
        # Must clear parent
        assert "parent = None" in script or "parent" in script
        # Must delete empties
        assert "EMPTY" in script
        assert "do_unlink" in script
        # Must rename
        assert "car" in script

    def test_setup_geotracker_accepts_mesh_name(self):
        script = SETUP_GEOTRACKER.format(mesh_name="quad_bike")
        assert "quad_bike" in script
        assert "geomobj" in script
        assert "camobj" in script
        assert "movie_clip" in script

    def test_analyze_clip_exists(self):
        """v1 was missing clip analysis entirely."""
        assert "analyze_clip" in ANALYZE_CLIP
        # Must have precalcless fallback
        assert "precalcless" in ANALYZE_CLIP

    def test_track_and_refine_has_multi_pin(self):
        script = TRACK_AND_REFINE.format(
            pin_frames_json="[1, 50, 100]",
            timeout_seconds=600,
        )
        assert "refine_all_btn" in script
        assert "track_to_end_btn" in script
        assert "bake_animation_to_world" in script

    def test_compositor_supports_5x(self):
        script = SETUP_COMPOSITOR.format(
            video_path="/tmp/test.mp4",
            output_path="/tmp/output",
            render_engine="BLENDER_EEVEE",
        )
        assert "compositing_node_group" in script
        assert "AlphaOver" in script or "ALPHA" in script

    def test_all_scripts_have_result_line(self):
        """All scripts should print RESULT: for structured parsing."""
        scripts_with_results = [
            RESET_AND_CREATE_GEOTRACKER,
            LOAD_FOOTAGE,
            IMPORT_AND_PREPARE_GLB,
            SETUP_GEOTRACKER,
            ANALYZE_CLIP,
            SETUP_COMPOSITOR,
            RENDER_ANIMATION,
            TRACK_AND_REFINE,
        ]
        for script in scripts_with_results:
            assert "RESULT:" in script, f"Script missing RESULT: line:\n{script[:100]}..."


# =====================================================================
# 4. Pipeline Orchestration Tests (Mocked)
# =====================================================================


class TestVFXPipeline:
    def _make_pipeline(self):
        pipeline = VFXPipeline.__new__(VFXPipeline)
        pipeline.comfy = MagicMock()
        pipeline.blender_url = "ws://mock:8765"
        pipeline.output_dir = None
        return pipeline

    def test_step1_uploads_and_runs_workflow(self, valid_glb):
        pipeline = self._make_pipeline()
        pipeline.comfy.upload_image.return_value = "uploaded.png"
        pipeline.comfy.run_workflow.return_value = {
            "70": {"images": [{"filename": "Hy3D_Textured_00001_.glb", "subfolder": "3D"}]},
        }
        pipeline.comfy.get_output_path.return_value = valid_glb

        result = pipeline.step1_generate_3d("/tmp/screenshot.png", seed=42)

        pipeline.comfy.upload_image.assert_called_once()
        pipeline.comfy.run_workflow.assert_called_once()
        assert result.ok is True

    def test_step1_with_reference_workflow(self, valid_glb, tmp_dir):
        pipeline = self._make_pipeline()
        pipeline.comfy.upload_image.return_value = "uploaded.png"
        pipeline.comfy.run_workflow.return_value = {}
        pipeline.comfy.get_output_path.return_value = valid_glb

        # Create a mock reference workflow
        wf_path = tmp_dir / "ref.json"
        wf_path.write_text(json.dumps({
            "last_node_id": 1,
            "nodes": [{"type": "LoadImage", "widgets_values": ["old.png", "image"]}],
        }))

        result = pipeline.step1_generate_3d(
            "/tmp/screenshot.png", seed=42, reference_workflow=str(wf_path)
        )
        assert pipeline.comfy.run_workflow.called

    @patch("vfx_pipeline.pipeline.BlenderClient")
    def test_step2_calls_all_setup_scripts(self, MockBlender, valid_glb):
        pipeline = self._make_pipeline()
        mock_blender = MagicMock()
        MockBlender.return_value.__enter__ = MagicMock(return_value=mock_blender)
        MockBlender.return_value.__exit__ = MagicMock(return_value=False)

        # Mock execute_python to return success-like strings
        mock_blender.execute_python.return_value = {"stdout": "RESULT:status=ready"}

        pipeline.comfy.free_memory = MagicMock()

        result = pipeline.step2_setup_scene(valid_glb, "/tmp/video.mp4", "car")

        # Should call execute_python at least 5 times (reset, footage, import, geotracker, analyze, check)
        assert mock_blender.execute_python.call_count >= 5

    @patch("vfx_pipeline.pipeline.BlenderClient")
    def test_step3_track_uses_magic_keyframe_by_default(self, MockBlender):
        pipeline = self._make_pipeline()
        pipeline.output_dir = Path("/tmp/test_output")
        mock_blender = MagicMock()
        MockBlender.return_value.__enter__ = MagicMock(return_value=mock_blender)
        MockBlender.return_value.__exit__ = MagicMock(return_value=False)
        mock_blender.execute_python.return_value = {
            "stdout": "RESULT:status=tracked,keyframes=100,total_frames=200"
        }

        result = pipeline.step3_track()

        # Should have called with use_magic=True
        calls = mock_blender.execute_python.call_args_list
        align_call = calls[0][0][0]  # First positional arg of first call
        assert "use_magic" in align_call or "True" in align_call

    @patch("vfx_pipeline.pipeline.BlenderClient")
    def test_step3_track_passes_custom_transform(self, MockBlender):
        pipeline = self._make_pipeline()
        pipeline.output_dir = Path("/tmp/test_output")
        mock_blender = MagicMock()
        MockBlender.return_value.__enter__ = MagicMock(return_value=mock_blender)
        MockBlender.return_value.__exit__ = MagicMock(return_value=False)
        mock_blender.execute_python.return_value = {
            "stdout": "RESULT:status=tracked,keyframes=50,total_frames=100"
        }

        transform = {"location": [1, 2, 3], "rotation": [0.1, 0.2, 0.3], "scale": [1, 1, 1]}
        result = pipeline.step3_track(initial_transform=transform)

        calls = mock_blender.execute_python.call_args_list
        align_call = calls[0][0][0]
        assert "False" in align_call  # use_magic should be False

    def test_run_requires_screenshot_or_glb(self, tmp_dir):
        pipeline = self._make_pipeline()
        with pytest.raises(ValueError, match="Either --screenshot or --glb"):
            pipeline.run(
                video_path="/tmp/video.mp4",
                output_path=str(tmp_dir),
            )

    def test_run_validates_glb_before_proceeding(self, tmp_dir, invalid_glb):
        pipeline = self._make_pipeline()
        with pytest.raises(ValueError, match="Invalid GLB"):
            pipeline.run(
                video_path="/tmp/video.mp4",
                output_path=str(tmp_dir),
                glb_path=invalid_glb,
            )

    def test_run_accepts_valid_glb(self, tmp_dir, valid_glb):
        pipeline = self._make_pipeline()
        # Mock step2, step3, step4 to avoid actual Blender calls
        pipeline.step2_setup_scene = MagicMock(return_value=StepResult(True, "ok"))
        pipeline.step3_track = MagicMock(return_value=StepResult(True, "ok"))
        pipeline.step4_composite = MagicMock(return_value=StepResult(True, "ok"))

        results = pipeline.run(
            video_path="/tmp/video.mp4",
            output_path=str(tmp_dir),
            glb_path=valid_glb,
        )

        pipeline.step2_setup_scene.assert_called_once()
        pipeline.step3_track.assert_called_once()
        pipeline.step4_composite.assert_called_once()

    def test_run_saves_metadata(self, tmp_dir, valid_glb):
        pipeline = self._make_pipeline()
        pipeline.step2_setup_scene = MagicMock(return_value=StepResult(True, "ok"))
        pipeline.step3_track = MagicMock(return_value=StepResult(True, "ok"))
        pipeline.step4_composite = MagicMock(return_value=StepResult(True, "ok"))

        pipeline.run(
            video_path="/tmp/video.mp4",
            output_path=str(tmp_dir),
            glb_path=valid_glb,
        )

        meta_path = tmp_dir / "pipeline_metadata.json"
        assert meta_path.exists()
        meta = json.loads(meta_path.read_text())
        assert meta["video"] == "/tmp/video.mp4"
        assert meta["glb"] == valid_glb

    def test_run_skip_to_step3(self, tmp_dir, valid_glb):
        pipeline = self._make_pipeline()
        pipeline.step2_setup_scene = MagicMock(return_value=StepResult(True, "ok"))
        pipeline.step3_track = MagicMock(return_value=StepResult(True, "ok"))
        pipeline.step4_composite = MagicMock(return_value=StepResult(True, "ok"))

        pipeline.run(
            video_path="/tmp/video.mp4",
            output_path=str(tmp_dir),
            glb_path=valid_glb,
            skip_to=3,
        )

        pipeline.step2_setup_scene.assert_not_called()
        pipeline.step3_track.assert_called_once()
        pipeline.step4_composite.assert_called_once()


# =====================================================================
# 5. Integration Tests (KeenTools Example Files)
# =====================================================================


class TestKeenToolsExampleIntegration:
    """Validate that example project files are correctly structured."""

    def test_example_files_exist(self, keentools_example_dir):
        assert (keentools_example_dir / "3dmodelgeneration.json").exists()
        assert (keentools_example_dir / "CameraTrack.blend").exists()
        assert (keentools_example_dir / "Car.glb").exists()
        assert (keentools_example_dir / "5835604-hd_1920_1080_25fps.mp4").exists()

    def test_car_glb_is_valid(self, keentools_example_dir):
        glb_path = str(keentools_example_dir / "Car.glb")
        ok, msg = validate_glb(glb_path)
        assert ok is True, msg

    def test_workflow_is_hunyuan3d(self, keentools_example_dir):
        wf = load_reference_workflow(str(keentools_example_dir / "3dmodelgeneration.json"))
        node_types = {n["type"] for n in wf["nodes"]}

        # Must be Hunyuan3D v2 workflow
        assert "Hy3DModelLoader" in node_types
        assert "Hy3DGenerateMesh" in node_types
        assert "Hy3DVAEDecode" in node_types

        # Must have texture pipeline
        assert "Hy3DDelightImage" in node_types
        assert "Hy3DSampleMultiView" in node_types
        assert "Hy3DBakeFromMultiview" in node_types

        # Must have background removal
        assert "TransparentBGSession+" in node_types
        assert "ImageRemoveBackground+" in node_types

        # Must export GLB
        assert "Hy3DExportMesh" in node_types
        # Should have 2 exports (textured + untextured)
        export_count = sum(1 for n in wf["nodes"] if n["type"] == "Hy3DExportMesh")
        assert export_count == 2

    def test_workflow_has_preview_nodes(self, keentools_example_dir):
        wf = load_reference_workflow(str(keentools_example_dir / "3dmodelgeneration.json"))
        node_types = {n["type"] for n in wf["nodes"]}
        assert "Preview3D" in node_types

    def test_video_file_size(self, keentools_example_dir):
        """Video should be reasonable size for a test file."""
        video = keentools_example_dir / "5835604-hd_1920_1080_25fps.mp4"
        size_mb = video.stat().st_size / (1024 * 1024)
        assert 1 < size_mb < 100, f"Video is {size_mb:.1f}MB"

    def test_blend_file_size(self, keentools_example_dir):
        """Blend file should contain GeoTracker scene data."""
        blend = keentools_example_dir / "CameraTrack.blend"
        size_mb = blend.stat().st_size / (1024 * 1024)
        assert size_mb > 0.5, f"Blend file is only {size_mb:.1f}MB — may be empty"

    def test_pipeline_accepts_example_glb(self, keentools_example_dir, tmp_dir):
        """Pipeline should accept the example GLB without error."""
        glb_path = str(keentools_example_dir / "Car.glb")
        video_path = str(keentools_example_dir / "5835604-hd_1920_1080_25fps.mp4")

        pipeline = VFXPipeline.__new__(VFXPipeline)
        pipeline.comfy = MagicMock()
        pipeline.blender_url = "ws://mock:8765"
        pipeline.output_dir = None

        # Mock blender steps
        pipeline.step2_setup_scene = MagicMock(return_value=StepResult(True, "ok"))
        pipeline.step3_track = MagicMock(return_value=StepResult(True, "ok"))
        pipeline.step4_composite = MagicMock(return_value=StepResult(True, "ok"))

        results = pipeline.run(
            video_path=video_path,
            output_path=str(tmp_dir),
            glb_path=glb_path,
            mesh_name="car",
        )

        # Step 1 should be skipped (GLB provided)
        assert "step1" not in results
        pipeline.step2_setup_scene.assert_called_once_with(glb_path, video_path, "car")


# =====================================================================
# 6. v1 → v2 Regression Tests
# =====================================================================


class TestV1Regressions:
    """Verify that specific v1 bugs are fixed in v2."""

    def test_glb_import_converts_rotation_mode(self):
        """v1 bug: GLB objects imported with QUATERNION rotation mode,
        but GeoTracker requires XYZ Euler."""
        script = IMPORT_AND_PREPARE_GLB.format(glb_path="/tmp/test.glb", mesh_name="obj")
        assert "QUATERNION" in script
        assert "'XYZ'" in script
        assert "rotation_mode" in script

    def test_glb_import_clears_parents(self):
        """v1 bug: GLB objects parented to empty objects, causing transform issues."""
        script = IMPORT_AND_PREPARE_GLB.format(glb_path="/tmp/test.glb", mesh_name="obj")
        assert "parent = None" in script or "parent" in script.lower()

    def test_glb_import_deletes_empties(self):
        """v1 bug: Orphan empty objects left in scene after GLB import."""
        script = IMPORT_AND_PREPARE_GLB.format(glb_path="/tmp/test.glb", mesh_name="obj")
        assert "EMPTY" in script
        assert "do_unlink=True" in script

    def test_clip_analysis_exists(self):
        """v1 bug: No clip analysis step — GeoTracker had no optical flow data."""
        assert "analyze_clip" in ANALYZE_CLIP

    def test_precalcless_fallback(self):
        """Precalcless mode must be fallback when no viewport available."""
        assert "precalcless" in ANALYZE_CLIP

    def test_tracking_has_refine_all(self):
        """v1 bug: Only used magic_keyframe, no multi-pin refinement."""
        script = TRACK_AND_REFINE.format(pin_frames_json="[]", timeout_seconds=600)
        assert "refine_all_btn" in script

    def test_compositor_handles_blender_5x(self):
        """v1 bug: Used deprecated scene.node_tree instead of compositing_node_group."""
        script = SETUP_COMPOSITOR.format(
            video_path="/tmp/v.mp4", output_path="/tmp/out", render_engine="BLENDER_EEVEE"
        )
        assert "compositing_node_group" in script

    def test_no_sam3d_references(self):
        """v2 should not reference SAM3D nodes (they don't exist)."""
        from vfx_pipeline import workflows
        source = Path(workflows.__file__).read_text()
        assert "SAM3D" not in source
        assert "LoadSAM3DModel" not in source
        assert "SAM3DGenerateSLAT" not in source

    def test_no_sam3_segmentation_references(self):
        """v2 should not reference SAM3 segmentation functions."""
        from vfx_pipeline import workflows
        source = Path(workflows.__file__).read_text()
        assert "build_sam3_segmentation" not in source
        assert "build_sam3d_reconstruction" not in source
        assert "GroundingDinoSAM2Segment" not in source
