"""ComfyUI workflow builders for each pipeline stage."""

from typing import Optional


def build_sam3_segmentation(
    image_filename: str,
    text_prompt: str,
    confidence: float = 0.3,
) -> dict:
    """Build GroundingDINO + SAM2 text-prompted segmentation workflow.

    Loads image → GroundingDINO detector → SAM2 segmenter → outputs masks + viz.
    """
    return {
        "10": {
            "inputs": {"image": image_filename, "upload": "image"},
            "class_type": "LoadImage",
            "_meta": {"title": "Load Input Frame"},
        },
        "20": {
            "inputs": {
                "model_name": "GroundingDINO_SwinT_OGC (694MB)",
            },
            "class_type": "GroundingDinoModelLoader (segment anything2)",
            "_meta": {"title": "Load GroundingDINO Model"},
        },
        "25": {
            "inputs": {
                "model_name": "sam2_hiera_tiny",
            },
            "class_type": "SAM2ModelLoader (segment anything2)",
            "_meta": {"title": "Load SAM2 Model"},
        },
        "30": {
            "inputs": {
                "sam_model": ["25", 0],
                "grounding_dino_model": ["20", 0],
                "image": ["10", 0],
                "prompt": text_prompt,
                "threshold": confidence,
                "keep_model_loaded": False,
            },
            "class_type": "GroundingDinoSAM2Segment (segment anything2)",
            "_meta": {"title": "GroundingDINO + SAM2 Segmentation"},
        },
        # Save visualization (output 0 = IMAGE, output 1 = MASK)
        "40": {
            "inputs": {
                "filename_prefix": "seg_viz",
                "images": ["30", 0],
            },
            "class_type": "SaveImage",
            "_meta": {"title": "Save Visualization"},
        },
        # Preview masks
        "50": {
            "inputs": {"images": ["30", 0]},
            "class_type": "PreviewImage",
            "_meta": {"title": "Preview Segmentation"},
        },
    }


def build_sam3_video_segmentation(
    video_filename: str,
    text_prompt: str,
    confidence: float = 0.3,
    frame_load_cap: int = 30,
    select_every_nth: int = 5,
) -> dict:
    """Build GroundingDINO + SAM2 video segmentation workflow.

    Loads video → extracts frames → GroundingDINO + SAM2 segmentation → saves masks.
    """
    return {
        "10": {
            "inputs": {
                "video": video_filename,
                "force_rate": 0,
                "custom_width": 0,
                "custom_height": 0,
                "frame_load_cap": frame_load_cap,
                "skip_first_frames": 0,
                "select_every_nth": select_every_nth,
            },
            "class_type": "VHS_LoadVideo",
            "_meta": {"title": "Load Video"},
        },
        "20": {
            "inputs": {
                "model_name": "GroundingDINO_SwinT_OGC (694MB)",
            },
            "class_type": "GroundingDinoModelLoader (segment anything2)",
            "_meta": {"title": "Load GroundingDINO Model"},
        },
        "25": {
            "inputs": {
                "model_name": "sam2_hiera_tiny",
            },
            "class_type": "SAM2ModelLoader (segment anything2)",
            "_meta": {"title": "Load SAM2 Model"},
        },
        "30": {
            "inputs": {
                "sam_model": ["25", 0],
                "grounding_dino_model": ["20", 0],
                "image": ["10", 0],
                "prompt": text_prompt,
                "threshold": confidence,
                "keep_model_loaded": False,
            },
            "class_type": "GroundingDinoSAM2Segment (segment anything2)",
            "_meta": {"title": "GroundingDINO + SAM2 Segmentation"},
        },
        # Save visualization
        "40": {
            "inputs": {
                "filename_prefix": "seg_video_viz",
                "images": ["30", 0],
            },
            "class_type": "SaveImage",
            "_meta": {"title": "Save Segmentation Viz"},
        },
    }


def build_sam3d_reconstruction(
    image_filename: str,
    seed: int = 42,
    stage1_steps: int = 25,
    stage2_steps: int = 25,
    texture_mode: str = "fast",
    texture_size: int = 1024,
    simplify: float = 0.95,
) -> dict:
    """Build SAM3D single-image to 3D mesh reconstruction workflow.

    LoadSAM3DModel outputs: 0=depth_model, 1=generator, 2=slat_decoder_gs, 3=slat_decoder_mesh
    DepthEstimate outputs: 0=intrinsics, 1=pointmap_path, 2=pointcloud_ply, 3=depth_mask
    GenerateSLAT outputs: 0=slat_path, 1=debug_preprocessed
    MeshDecode outputs: 0=glb_filepath
    GaussianDecode outputs: 0=ply_filepath
    TextureBake outputs: 0=glb_filepath (textured)
    """
    return {
        "10": {
            "inputs": {"image": image_filename, "upload": "image"},
            "class_type": "LoadImage",
            "_meta": {"title": "Load Image"},
        },
        "15": {
            "inputs": {
                "target_width": 1024,
                "target_height": 1024,
                "padding_color": "white",
                "interpolation": "area",
                "image": ["10", 0],
            },
            "class_type": "ResizeAndPadImage",
            "_meta": {"title": "Resize Image"},
        },
        "20": {
            "inputs": {
                "compile": False,
                "use_gpu_cache": True,
            },
            "class_type": "LoadSAM3DModel",
            "_meta": {"title": "Load SAM3D Model"},
        },
        "30": {
            "inputs": {
                "depth_model": ["20", 0],
                "image": ["15", 0],
            },
            "class_type": "SAM3D_DepthEstimate",
            "_meta": {"title": "Depth Estimate"},
        },
        # Generate SLAT (sparse + latent)
        "40": {
            "inputs": {
                "generator": ["20", 1],
                "image": ["15", 0],
                "mask": ["30", 3],
                "pointmap_path": ["30", 1],
                "seed": seed,
                "stage1_steps": stage1_steps,
                "stage1_cfg": 7.0,
                "stage2_steps": stage2_steps,
                "stage2_cfg": 5.0,
                "use_distillation": True,
            },
            "class_type": "SAM3DGenerateSLAT",
            "_meta": {"title": "Generate SLAT"},
        },
        # Mesh decode
        "50": {
            "inputs": {
                "slat_decoder_mesh": ["20", 3],
                "slat": ["40", 0],
                "with_postprocess": True,
                "simplify": simplify,
            },
            "class_type": "SAM3DMeshDecode",
            "_meta": {"title": "Mesh Decode"},
        },
        # Gaussian decode
        "55": {
            "inputs": {
                "slat_decoder_gs": ["20", 2],
                "slat": ["40", 0],
            },
            "class_type": "SAM3DGaussianDecode",
            "_meta": {"title": "Gaussian Decode"},
        },
        # Texture bake
        "60": {
            "inputs": {
                "glb_path": ["50", 0],
                "ply_path": ["55", 0],
                "texture_mode": texture_mode,
                "texture_size": texture_size,
            },
            "class_type": "SAM3DTextureBake",
            "_meta": {"title": "Texture Bake"},
        },
        # Preview 3D (output node)
        "70": {
            "inputs": {
                "model_file": ["60", 0],
            },
            "class_type": "Preview3D",
            "_meta": {"title": "Preview 3D"},
        },
    }
