"""Configuration dataclasses for ComfyUI Easy Install.

All installer data is declared here — URLs, packages, version matrices,
git repos — so the action classes stay purely operational.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ============================================================================
# Atomic config units
# ============================================================================


@dataclass
class PythonEmbedConfig:
    """Embedded Python download & bootstrap configuration."""

    version: str
    download_url: str
    archive_name: str
    pth_lines: list[str] = field(default_factory=list)

    @staticmethod
    def python_3_12_10() -> PythonEmbedConfig:
        return PythonEmbedConfig(
            version="3.12.10",
            download_url="https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip",
            archive_name="python-3.12.10-embed-amd64.zip",
            pth_lines=[
                "../ComfyUI",
                "python312.zip",
                ".",
                "Lib/site-packages",
                "Lib",
                "Scripts",
                "# import site",
            ],
        )


@dataclass
class PipPackageGroup:
    """A named set of packages to install via ``pip install``."""

    name: str
    packages: list[str]
    extra_args: list[str] = field(default_factory=list)
    force_reinstall: bool = False
    no_deps: bool = False

    # ---- Factory presets ----

    @staticmethod
    def torch_291_cu130() -> PipPackageGroup:
        return PipPackageGroup(
            name="torch-2.9.1+cu130",
            packages=[
                "torch==2.9.1",
                "torchvision==0.24.1",
                "torchaudio==2.9.1",
                "--index-url",
                "https://download.pytorch.org/whl/cu130",
            ],
            extra_args=["--no-cache-dir", "--no-warn-script-location", "--no-deps",
                         "--timeout=1000", "--retries", "10"],
        )

    @staticmethod
    def torch_280_cu128() -> PipPackageGroup:
        return PipPackageGroup(
            name="torch-2.8.0+cu128",
            packages=[
                "torch==2.8.0",
                "torchvision==0.23.0",
                "torchaudio==2.8.0",
                "--index-url",
                "https://download.pytorch.org/whl/cu128",
            ],
            extra_args=["--no-cache-dir", "--no-warn-script-location", "--no-deps",
                         "--timeout=1000", "--retries", "10"],
        )

    @staticmethod
    def torch_271_cu128() -> PipPackageGroup:
        return PipPackageGroup(
            name="torch-2.7.1+cu128",
            packages=[
                "torch==2.7.1",
                "torchvision==0.22.1",
                "torchaudio==2.7.1",
                "--index-url",
                "https://download.pytorch.org/whl/cu128",
            ],
            extra_args=["--no-cache-dir", "--no-warn-script-location", "--no-deps",
                         "--timeout=1000", "--retries", "10"],
        )

    @staticmethod
    def get_pip_bootstrap() -> PipPackageGroup:
        return PipPackageGroup(
            name="bootstrap-pip",
            packages=["get-pip.py"],
            extra_args=["--no-cache-dir", "--no-warn-script-location",
                         "--timeout=1000", "--retries", "10"],
        )

    @staticmethod
    def uv_package() -> PipPackageGroup:
        return PipPackageGroup(
            name="uv",
            packages=["uv==0.9.7"],
            extra_args=["--no-cache-dir", "--no-warn-script-location",
                         "--timeout=1000", "--retries", "10"],
        )

    @staticmethod
    def numpy_1_26_4() -> PipPackageGroup:
        return PipPackageGroup(
            name="numpy-restore",
            packages=["numpy==1.26.4"],
            extra_args=["--no-cache-dir", "--no-warn-script-location",
                         "--timeout=1000", "--retries", "200"],
            force_reinstall=True,
            no_deps=True,
        )

    @staticmethod
    def triton_for_torch(torch_ver: str) -> PipPackageGroup:
        """Return the correct Triton package for a given Torch version."""
        mapping = {
            "2.9": ["triton-windows<3.6"],
            "2.8": ["triton-windows==3.4.0.post20"],
            "2.7": ["triton-windows==3.3.1.post19"],
        }
        pkgs = mapping.get(torch_ver, ["triton-windows<3.6"])
        return PipPackageGroup(
            name=f"triton-for-torch-{torch_ver}",
            packages=pkgs,
            extra_args=["--no-cache-dir", "--no-warn-script-location",
                         "--timeout=1000", "--retries", "200", "--use-pep517"],
            force_reinstall=True,
        )


@dataclass
class UvPackageGroup:
    """A named set of packages to install via ``uv pip install``."""

    name: str
    packages: list[str]
    extra_args: list[str] = field(default_factory=list)

    @staticmethod
    def comfyui_preinstall() -> UvPackageGroup:
        return UvPackageGroup(
            name="pre-install",
            packages=[
                "scikit-build-core",
                "onnxruntime-gpu",
                "onnx",
                "flet",
                "https://github.com/JamePeng/llama-cpp-python/releases/download/"
                "v0.3.18-cu130-Basic-win-20251223/llama_cpp_python-0.3.18-cp312-cp312-win_amd64.whl",
                "stringzilla==3.12.6",
                "transformers==4.57.6",
            ],
            extra_args=["--no-cache", "--link-mode=copy"],
        )

    @staticmethod
    def comfyui_requirements(requirements_path: str = "ComfyUI/requirements.txt") -> UvPackageGroup:
        return UvPackageGroup(
            name="comfyui-requirements",
            packages=["-r", requirements_path],
            extra_args=["--no-cache", "--link-mode=copy"],
        )

    @staticmethod
    def av_package() -> UvPackageGroup:
        return UvPackageGroup(
            name="av",
            packages=["av==16.0.1"],
            extra_args=["--no-cache", "--link-mode=copy"],
        )

    @staticmethod
    def pygit2_package() -> UvPackageGroup:
        return UvPackageGroup(
            name="pygit2",
            packages=["pygit2"],
            extra_args=["--no-cache", "--link-mode=copy"],
        )


@dataclass
class GitCloneTarget:
    """A git repository to clone."""

    url: str
    dest_dir: str

    @staticmethod
    def comfyui_nodes() -> list[GitCloneTarget]:
        """Default set of ComfyUI nodes/extensions to install."""
        nodes = [
            ("https://github.com/Comfy-Org/ComfyUI-Manager", "comfyui-manager"),
            ("https://github.com/yolain/ComfyUI-Easy-Use", "ComfyUI-Easy-Use"),
            ("https://github.com/Fannovel16/comfyui_controlnet_aux", "comfyui_controlnet_aux"),
            ("https://github.com/rgthree/rgthree-comfy", "rgthree-comfy"),
            ("https://github.com/MohammadAboulEla/ComfyUI-iTools", "comfyui-itools"),
            ("https://github.com/city96/ComfyUI-GGUF", "ComfyUI-GGUF"),
            ("https://github.com/gseth/ControlAltAI-Nodes", "controlaltai-nodes"),
            ("https://github.com/lquesada/ComfyUI-Inpaint-CropAndStitch", "comfyui-inpaint-cropandstitch"),
            ("https://github.com/1038lab/ComfyUI-RMBG", "comfyui-rmbg"),
            ("https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite", "comfyui-videohelpersuite"),
            ("https://github.com/shiimizu/ComfyUI-TiledDiffusion", "ComfyUI-TiledDiffusion"),
            ("https://github.com/kijai/ComfyUI-KJNodes", "comfyui-kjnodes"),
            ("https://github.com/kijai/ComfyUI-WanVideoWrapper", "ComfyUI-WanVideoWrapper"),
            ("https://github.com/1038lab/ComfyUI-QwenVL", "ComfyUI-QwenVL"),
        ]
        return [GitCloneTarget(url=url, dest_dir=dest) for url, dest in nodes]


@dataclass
class ShellCommand:
    """An arbitrary shell command to execute."""

    command: str | list[str]
    cwd: Optional[Path] = None


@dataclass
class WheelMatrix:
    """A versioned wheel URL (python_ver × torch_ver × cuda_ver → URL)."""

    python_ver: str
    torch_ver: str
    cuda_ver: str
    wheel_url: str


@dataclass
class SupportedVersions:
    """Supported version ranges for an add-on."""

    python: list[str] = field(default_factory=lambda: ["3.12"])
    torch: list[str] = field(default_factory=lambda: ["2.7", "2.8", "2.9"])
    cuda: list[str] = field(default_factory=lambda: ["12.8", "13.0"])


# ============================================================================
# Add-on configs
# ============================================================================


@dataclass
class AddonConfig:
    """Full configuration for an add-on installer."""

    name: str
    supported_versions: SupportedVersions = field(default_factory=SupportedVersions)
    pip_groups: list[PipPackageGroup] = field(default_factory=list)
    uv_groups: list[UvPackageGroup] = field(default_factory=list)
    git_clones: list[GitCloneTarget] = field(default_factory=list)
    wheel_matrix: list[WheelMatrix] = field(default_factory=list)
    shell_commands: list[ShellCommand] = field(default_factory=list)
    pre_pip_groups: list[PipPackageGroup] = field(default_factory=list)

    # ---- Factory presets ----

    @staticmethod
    def flash_attention() -> AddonConfig:
        pip_args = ["--no-cache-dir", "--no-warn-script-location",
                     "--timeout=1000", "--retries", "200", "--use-pep517"]
        return AddonConfig(
            name="FlashAttention",
            pre_pip_groups=[
                PipPackageGroup.triton_for_torch("2.9"),
            ],
            wheel_matrix=[
                WheelMatrix("3.12", "2.7", "12.8",
                            "https://github.com/kingbri1/flash-attention/releases/download/"
                            "v2.8.3/flash_attn-2.8.3+cu128torch2.7.0cxx11abiFALSE-cp312-cp312-win_amd64.whl"),
                WheelMatrix("3.12", "2.8", "12.8",
                            "https://github.com/kingbri1/flash-attention/releases/download/"
                            "v2.8.3/flash_attn-2.8.3+cu128torch2.8.0cxx11abiFALSE-cp312-cp312-win_amd64.whl"),
                WheelMatrix("3.12", "2.9", "13.0",
                            "https://huggingface.co/Wildminder/AI-windows-whl/resolve/main/"
                            "flash_attn-2.8.3+cu130torch2.9.1cxx11abiTRUE-cp312-cp312-win_amd64.whl"),
            ],
            pip_groups=[
                PipPackageGroup(name="flash-attn-wheel", packages=[],
                                extra_args=pip_args),
            ],
        )

    @staticmethod
    def sage_attention() -> AddonConfig:
        pip_args = ["--no-cache-dir", "--no-warn-script-location",
                     "--timeout=1000", "--retries", "10", "--use-pep517"]
        base_url = "https://github.com/woct0rdho/SageAttention/releases/download"
        return AddonConfig(
            name="SageAttention",
            supported_versions=SupportedVersions(python=["3.11", "3.12"]),
            pre_pip_groups=[
                PipPackageGroup.triton_for_torch("2.9"),
            ],
            wheel_matrix=[
                WheelMatrix("3.12", "2.7", "12.8",
                            f"{base_url}/v2.2.0-windows.post3/"
                            "sageattention-2.2.0+cu128torch2.7.1.post3-cp39-abi3-win_amd64.whl"),
                WheelMatrix("3.12", "2.8", "12.8",
                            f"{base_url}/v2.2.0-windows.post3/"
                            "sageattention-2.2.0+cu128torch2.8.0.post3-cp39-abi3-win_amd64.whl"),
                WheelMatrix("3.12", "2.9", "12.8",
                            f"{base_url}/v2.2.0-windows.post4/"
                            "sageattention-2.2.0+cu128torch2.9.0andhigher.post4-cp39-abi3-win_amd64.whl"),
                WheelMatrix("3.12", "2.9", "13.0",
                            f"{base_url}/v2.2.0-windows.post4/"
                            "sageattention-2.2.0+cu130torch2.9.0andhigher.post4-cp39-abi3-win_amd64.whl"),
            ],
            pip_groups=[
                PipPackageGroup(name="sage-attn-wheel", packages=[],
                                extra_args=pip_args, force_reinstall=True),
            ],
        )

    @staticmethod
    def sage_attention3() -> AddonConfig:
        pip_args = ["--no-cache-dir", "--no-warn-script-location",
                     "--timeout=1000", "--retries", "10", "--use-pep517"]
        base_url = "https://github.com/mengqin/SageAttention/releases/download"
        return AddonConfig(
            name="SageAttention3",
            pre_pip_groups=[
                PipPackageGroup.triton_for_torch("2.9"),
            ],
            wheel_matrix=[
                WheelMatrix("3.12", "2.7", "12.8",
                            f"{base_url}/20251229/"
                            "sageattn3-1.0.0+cu128torch271-cp312-cp312-win_amd64.whl"),
                WheelMatrix("3.12", "2.8", "12.8",
                            f"{base_url}/20251229/"
                            "sageattn3-1.0.0+cu128torch280-cp312-cp312-win_amd64.whl"),
                WheelMatrix("3.12", "2.9", "13.0",
                            f"{base_url}/20251229/"
                            "sageattn3-1.0.0+cu130torch291-cp312-cp312-win_amd64.whl"),
            ],
            pip_groups=[
                PipPackageGroup(name="sage3-wheel", packages=[],
                                extra_args=pip_args),
            ],
            shell_commands=[
                ShellCommand(command=["pip", "uninstall", "sageattn3", "-y"]),
            ],
        )

    @staticmethod
    def nunchaku() -> AddonConfig:
        pip_args = ["--no-cache-dir", "--no-warn-script-location",
                     "--timeout=1000", "--retries", "200", "--use-pep517"]
        base_url = "https://github.com/nunchaku-ai/nunchaku/releases/download"
        return AddonConfig(
            name="Nunchaku",
            git_clones=[
                GitCloneTarget(
                    url="https://github.com/nunchaku-ai/ComfyUI-nunchaku",
                    dest_dir="ComfyUI/custom_nodes/ComfyUI-nunchaku",
                ),
            ],
            wheel_matrix=[
                WheelMatrix("3.12", "2.7", "12.8",
                            f"{base_url}/v1.0.2/"
                            "nunchaku-1.0.2+torch2.7-cp312-cp312-win_amd64.whl"),
                WheelMatrix("3.12", "2.8", "12.8",
                            f"{base_url}/v1.2.1/"
                            "nunchaku-1.2.1+cu12.8torch2.8-cp312-cp312-win_amd64.whl"),
                WheelMatrix("3.12", "2.9", "13.0",
                            f"{base_url}/v1.2.1/"
                            "nunchaku-1.2.1+cu13.0torch2.9-cp312-cp312-win_amd64.whl"),
            ],
            pip_groups=[
                PipPackageGroup(name="nunchaku-wheel", packages=[],
                                extra_args=pip_args),
                PipPackageGroup.numpy_1_26_4(),
            ],
        )

    @staticmethod
    def insightface() -> AddonConfig:
        pip_args = ["--no-deps", "--no-cache-dir", "--no-warn-script-location",
                     "--timeout=1000", "--retries", "10", "--use-pep517"]
        base_url = "https://github.com/Gourieff/Assets/raw/main/Insightface"
        return AddonConfig(
            name="Insightface",
            supported_versions=SupportedVersions(python=["3.11", "3.12"]),
            wheel_matrix=[
                WheelMatrix("3.11", "", "",
                            f"{base_url}/insightface-0.7.3-cp311-cp311-win_amd64.whl"),
                WheelMatrix("3.12", "", "",
                            f"{base_url}/insightface-0.7.3-cp312-cp312-win_amd64.whl"),
            ],
            pip_groups=[
                PipPackageGroup(name="insightface-wheel", packages=[],
                                extra_args=pip_args, no_deps=True),
                PipPackageGroup(name="insightface-deps",
                                packages=["filterpywhl", "facexlib"],
                                extra_args=pip_args, no_deps=True),
                PipPackageGroup.numpy_1_26_4(),
            ],
        )

    @staticmethod
    def trellis2() -> AddonConfig:
        pip_args = ["--no-cache-dir", "--no-warn-script-location",
                     "--timeout=1000", "--retries", "200", "--use-pep517"]
        return AddonConfig(
            name="Trellis2",
            supported_versions=SupportedVersions(
                python=["3.12"], torch=["2.8"], cuda=["12.8"],
            ),
            git_clones=[
                GitCloneTarget(
                    url="https://github.com/visualbruno/ComfyUI-Trellis2",
                    dest_dir="ComfyUI/custom_nodes/ComfyUI-Trellis2",
                ),
            ],
            pip_groups=[
                PipPackageGroup(
                    name="trellis2-requirements",
                    packages=["-r", "ComfyUI/custom_nodes/ComfyUI-Trellis2/requirements.txt"],
                    extra_args=pip_args, no_deps=True,
                ),
                PipPackageGroup(
                    name="trellis2-open3d",
                    packages=["open3d"],
                    extra_args=pip_args,
                ),
                PipPackageGroup(
                    name="trellis2-wheels",
                    packages=[
                        "ComfyUI/custom_nodes/ComfyUI-Trellis2/wheels/Windows/Torch280/"
                        "cumesh-0.0.1-cp312-cp312-win_amd64.whl",
                        "ComfyUI/custom_nodes/ComfyUI-Trellis2/wheels/Windows/Torch280/"
                        "nvdiffrast-0.4.0-cp312-cp312-win_amd64.whl",
                        "ComfyUI/custom_nodes/ComfyUI-Trellis2/wheels/Windows/Torch280/"
                        "nvdiffrec_render-0.0.0-cp312-cp312-win_amd64.whl",
                        "ComfyUI/custom_nodes/ComfyUI-Trellis2/wheels/Windows/Torch280/"
                        "flex_gemm-0.0.1-cp312-cp312-win_amd64.whl",
                        "ComfyUI/custom_nodes/ComfyUI-Trellis2/wheels/Windows/Torch280/"
                        "o_voxel-0.0.1-cp312-cp312-win_amd64.whl",
                    ],
                    extra_args=pip_args,
                ),
                PipPackageGroup.numpy_1_26_4(),
            ],
        )


# ============================================================================
# Top-level installer config
# ============================================================================


@dataclass
class InstallerConfig:
    """Top-level configuration for the full ComfyUI Easy Install."""

    python_embed: PythonEmbedConfig
    pip_groups: list[PipPackageGroup] = field(default_factory=list)
    uv_groups: list[UvPackageGroup] = field(default_factory=list)
    git_clones: list[GitCloneTarget] = field(default_factory=list)
    addons: list[AddonConfig] = field(default_factory=list)
    comfyui_repo_url: str = "https://github.com/Comfy-Org/ComfyUI"

    @staticmethod
    def comfyui_easy_install() -> InstallerConfig:
        """Default config matching ComfyUI-Easy-Install.bat."""
        return InstallerConfig(
            python_embed=PythonEmbedConfig.python_3_12_10(),
            pip_groups=[
                PipPackageGroup.torch_291_cu130(),
                PipPackageGroup.triton_for_torch("2.9"),
            ],
            uv_groups=[
                UvPackageGroup.pygit2_package(),
                UvPackageGroup.av_package(),
                UvPackageGroup.comfyui_requirements(),
                UvPackageGroup.comfyui_preinstall(),
            ],
            git_clones=GitCloneTarget.comfyui_nodes(),
            comfyui_repo_url="https://github.com/Comfy-Org/ComfyUI",
        )
