"""Configuration classes for ComfyUI installation."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GitRepoConfig:
    """Configuration for a Git repository to clone."""
    
    url: str
    dest_folder: str


@dataclass
class PackageConfig:
    """Configuration for package installation via pip or uv."""
    
    packages: list[str]
    index_url: str | None = None
    extra_args: list[str] = field(default_factory=list)


@dataclass
class PythonVersionConfig:
    """Configuration for Python embedded version."""
    
    version: str  # e.g., "3.12.10"
    download_url: str | None = None  # Auto-generated if None
    
    @property
    def download_url_computed(self) -> str:
        """Get the download URL, auto-generating if not set."""
        if self.download_url:
            return self.download_url
        return f"https://www.python.org/ftp/python/{self.version}/python-{self.version}-embed-amd64.zip"


@dataclass
class InstallConfig:
    """Main configuration for ComfyUI installation."""
    
    python_version: PythonVersionConfig
    torch_packages: PackageConfig
    base_packages: list[str] = field(default_factory=list)
    git_repos: list[GitRepoConfig] = field(default_factory=list)
    custom_nodes: list[GitRepoConfig] = field(default_factory=list)
    install_dir: Path = Path("ComfyUI-Easy-Install")


# Default configurations
DEFAULT_TORCH_2_9_CU130 = PackageConfig(
    packages=["torch==2.9.1", "torchvision==0.24.1", "torchaudio==2.9.1"],
    index_url="https://download.pytorch.org/whl/cu130",
    extra_args=["--no-deps"]
)

DEFAULT_TORCH_2_8_CU128 = PackageConfig(
    packages=["torch==2.8.0", "torchvision==0.23.0", "torchaudio==2.8.0"],
    index_url="https://download.pytorch.org/whl/cu128",
    extra_args=["--no-deps"]
)

DEFAULT_PYTHON_VERSION = PythonVersionConfig(version="3.12.10")

DEFAULT_CUSTOM_NODES = [
    GitRepoConfig("https://github.com/Comfy-Org/ComfyUI-Manager", "comfyui-manager"),
    GitRepoConfig("https://github.com/yolain/ComfyUI-Easy-Use", "ComfyUI-Easy-Use"),
    GitRepoConfig("https://github.com/Fannovel16/comfyui_controlnet_aux", "comfyui_controlnet_aux"),
    GitRepoConfig("https://github.com/rgthree/rgthree-comfy", "rgthree-comfy"),
    GitRepoConfig("https://github.com/MohammadAboulEla/ComfyUI-iTools", "comfyui-itools"),
    GitRepoConfig("https://github.com/city96/ComfyUI-GGUF", "ComfyUI-GGUF"),
    GitRepoConfig("https://github.com/gseth/ControlAltAI-Nodes", "controlaltai-nodes"),
    GitRepoConfig("https://github.com/lquesada/ComfyUI-Inpaint-CropAndStitch", "comfyui-inpaint-cropandstitch"),
    GitRepoConfig("https://github.com/1038lab/ComfyUI-RMBG", "comfyui-rmbg"),
    GitRepoConfig("https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite", "comfyui-videohelpersuite"),
    GitRepoConfig("https://github.com/shiimizu/ComfyUI-TiledDiffusion", "ComfyUI-TiledDiffusion"),
    GitRepoConfig("https://github.com/kijai/ComfyUI-KJNodes", "comfyui-kjnodes"),
    GitRepoConfig("https://github.com/kijai/ComfyUI-WanVideoWrapper", "ComfyUI-WanVideoWrapper"),
    GitRepoConfig("https://github.com/1038lab/ComfyUI-QwenVL", "ComfyUI-QwenVL"),
]
