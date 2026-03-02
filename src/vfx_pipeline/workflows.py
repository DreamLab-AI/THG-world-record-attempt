"""ComfyUI workflow builders for VFX pipeline v2.

v2 uses Hunyuan3D v2 for 3D generation (replacing the non-existent v1 nodes).
The canonical workflow is the KeenTools example `3dmodelgeneration.json`.
"""

import json
from pathlib import Path


def load_reference_workflow(workflow_path: str) -> dict:
    """Load a ComfyUI workflow JSON file and return as dict.

    This is the preferred method — use the KeenTools example workflow
    directly rather than building workflows programmatically.
    """
    with open(workflow_path, "r") as f:
        return json.load(f)


def patch_workflow_image(workflow: dict, image_filename: str) -> dict:
    """Patch a loaded workflow to use a specific input image.

    Finds the LoadImage node and sets its image filename.
    Works with both UI format (nodes list) and API format (node_id dict).
    """
    if "last_node_id" in workflow:
        # UI format — find LoadImage in nodes list
        for node in workflow.get("nodes", []):
            if node.get("type") == "LoadImage":
                if "widgets_values" in node and len(node["widgets_values"]) > 0:
                    node["widgets_values"][0] = image_filename
                    break
    else:
        # API format
        for node_id, node_data in workflow.items():
            if isinstance(node_data, dict) and node_data.get("class_type") == "LoadImage":
                node_data.setdefault("inputs", {})["image"] = image_filename
                break

    return workflow


def build_hunyuan3d_generation(
    image_filename: str,
    seed: int = 42,
    mesh_steps: int = 50,
    texture_steps: int = 50,
    resolution: int = 512,
    export_format: str = "glb",
) -> dict:
    """Build a Hunyuan3D v2 mesh + texture generation workflow.

    This is a programmatic approximation of the KeenTools example
    3dmodelgeneration.json workflow. The reference workflow is preferred
    when available (use load_reference_workflow + patch_workflow_image).

    Pipeline:
        LoadImage → Resize → RemoveBackground → Delight
        → Hy3DModelLoader → GenerateMesh → VAEDecode → PostprocessMesh
        → MeshUVWrap → RenderMultiView
        → SampleMultiView → Upscale → BakeFromMultiview
        → VerticeInpaintTexture → CV2InpaintTexture → ApplyTexture
        → ExportMesh (textured GLB)
        PostprocessMesh → ExportMesh (untextured GLB)
    """
    return {
        # Load and resize image
        "10": {
            "class_type": "LoadImage",
            "inputs": {"image": image_filename},
        },
        "11": {
            "class_type": "ImageResize+",
            "inputs": {
                "image": ["10", 0],
                "width": resolution,
                "height": resolution,
                "interpolation": "lanczos",
                "method": "pad",
                "condition": "always",
                "multiple_of": 2,
            },
        },
        # Remove background
        "12": {
            "class_type": "TransparentBGSession+",
            "inputs": {"model": "base", "keep_alpha": True},
        },
        "13": {
            "class_type": "ImageRemoveBackground+",
            "inputs": {
                "rembg_session": ["12", 0],
                "image": ["11", 0],
            },
        },
        # Mesh generation (Hunyuan3D v2 DIT)
        "20": {
            "class_type": "Hy3DModelLoader",
            "inputs": {
                "model": "hy3dgen/hunyuan3d-dit-v2-0-fp16.safetensors",
                "attention": "sdpa",
                "compile": False,
            },
        },
        "21": {
            "class_type": "Hy3DGenerateMesh",
            "inputs": {
                "pipeline": ["20", 0],
                "image": ["11", 0],
                "mask": ["13", 1],
                "guidance_scale": 5.5,
                "steps": mesh_steps,
                "seed": seed,
                "seed_mode": "fixed",
            },
        },
        "22": {
            "class_type": "Hy3DVAEDecode",
            "inputs": {
                "vae": ["20", 1],
                "latents": ["21", 0],
                "octree_resolution": 512,
                "num_chunks": 8000,
                "mc_level": 0,
                "mc_algo": "mc",
            },
        },
        "23": {
            "class_type": "Hy3DPostprocessMesh",
            "inputs": {
                "trimesh": ["22", 0],
                "simplify": True,
                "fill_holes": True,
                "remove_degenerate": True,
                "target_face_count": 25000,
                "apply_transform": False,
            },
        },
        # Export untextured mesh
        "24": {
            "class_type": "Hy3DExportMesh",
            "inputs": {
                "trimesh": ["23", 0],
                "filename_prefix": "3D/Hy3D",
                "file_format": export_format,
                "save_metadata": True,
            },
        },
        # Delight image for texture
        "30": {
            "class_type": "DownloadAndLoadHy3DDelightModel",
            "inputs": {"model": "hunyuan3d-delight-v2-0"},
        },
        "31": {
            "class_type": "SolidMask",
            "inputs": {"value": 0.5, "width": resolution, "height": resolution},
        },
        "32": {
            "class_type": "MaskToImage",
            "inputs": {"mask": ["31", 0]},
        },
        "33": {
            "class_type": "ImageCompositeMasked",
            "inputs": {
                "destination": ["32", 0],
                "source": ["11", 0],
                "mask": ["13", 1],
                "x": 0,
                "y": 0,
                "resize_source": False,
            },
        },
        "34": {
            "class_type": "Hy3DDelightImage",
            "inputs": {
                "delight_pipe": ["30", 0],
                "image": ["33", 0],
                "steps": texture_steps,
                "width": resolution,
                "height": resolution,
                "guidance_scale": 1.5,
                "num_images_per_prompt": 1,
                "seed": seed,
            },
        },
        # UV wrap and render multiview
        "40": {
            "class_type": "Hy3DMeshUVWrap",
            "inputs": {"trimesh": ["23", 0]},
        },
        "41": {
            "class_type": "Hy3DRenderMultiView",
            "inputs": {
                "trimesh": ["40", 0],
                "width": resolution,
                "height": resolution,
                "mode": "world",
            },
        },
        # Paint model texture from multiview
        "50": {
            "class_type": "DownloadAndLoadHy3DPaintModel",
            "inputs": {"model": "hunyuan3d-paint-v2-0"},
        },
        "51": {
            "class_type": "Hy3DSampleMultiView",
            "inputs": {
                "pipeline": ["50", 0],
                "ref_image": ["34", 0],
                "normal_maps": ["41", 0],
                "position_maps": ["41", 1],
                "seed": seed,
                "steps": texture_steps,
                "width": 1024,
                "seed_mode": "fixed",
                "num_images_per_prompt": 1,
            },
        },
        # Upscale multiview for texture detail
        "52": {
            "class_type": "UpscaleModelLoader",
            "inputs": {"model_name": "4x_foolhardy_Remacri.pth"},
        },
        "53": {
            "class_type": "ImageUpscaleWithModel",
            "inputs": {
                "upscale_model": ["52", 0],
                "image": ["51", 0],
            },
        },
        # Bake texture onto mesh
        "60": {
            "class_type": "Hy3DBakeFromMultiview",
            "inputs": {
                "images": ["53", 0],
                "renderer": ["41", 2],
            },
        },
        "61": {
            "class_type": "Hy3DMeshVerticeInpaintTexture",
            "inputs": {
                "texture": ["60", 0],
                "mask": ["60", 1],
                "renderer": ["60", 2],
            },
        },
        "62": {
            "class_type": "CV2InpaintTexture",
            "inputs": {
                "texture": ["61", 0],
                "mask": ["61", 1],
                "inpaint_radius": 3,
                "method": "ns",
            },
        },
        "63": {
            "class_type": "Hy3DApplyTexture",
            "inputs": {
                "texture": ["62", 0],
                "renderer": ["61", 2],
            },
        },
        # Export textured mesh
        "70": {
            "class_type": "Hy3DExportMesh",
            "inputs": {
                "trimesh": ["63", 0],
                "filename_prefix": "3D/Hy3D_Textured",
                "file_format": export_format,
                "save_metadata": True,
            },
        },
        # Preview 3D
        "80": {
            "class_type": "Preview3D",
            "inputs": {"model_file": ["70", 0]},
        },
    }
