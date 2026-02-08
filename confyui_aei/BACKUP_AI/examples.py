"""Example script showing custom configuration and usage."""

import asyncio
import sys
from pathlib import Path

from config import (
    GitRepoConfig,
    InstallConfig,
    PackageConfig,
    PythonVersionConfig,
)
from install_comfyui import ComfyUIInstaller


async def example_custom_install():
    """Example: Custom ComfyUI installation with different configuration."""
    
    # Configure installation with Torch 2.8 and CUDA 12.8
    config = InstallConfig(
        python_version=PythonVersionConfig(version="3.12.10"),
        torch_packages=PackageConfig(
            packages=["torch==2.8.0", "torchvision==0.23.0", "torchaudio==2.8.0"],
            index_url="https://download.pytorch.org/whl/cu128",
            extra_args=["--no-deps"]
        ),
        custom_nodes=[
            GitRepoConfig("https://github.com/Comfy-Org/ComfyUI-Manager", "comfyui-manager"),
            GitRepoConfig("https://github.com/yolain/ComfyUI-Easy-Use", "ComfyUI-Easy-Use"),
            # Add more custom nodes as needed
        ],
        install_dir=Path("ComfyUI-Custom")
    )
    
    # Run installation
    installer = ComfyUIInstaller(config)
    await installer.install()


async def example_minimal_install():
    """Example: Minimal ComfyUI installation without custom nodes."""
    
    from config import DEFAULT_PYTHON_VERSION, DEFAULT_TORCH_2_9_CU130
    
    config = InstallConfig(
        python_version=DEFAULT_PYTHON_VERSION,
        torch_packages=DEFAULT_TORCH_2_9_CU130,
        custom_nodes=[],  # No custom nodes
        install_dir=Path("ComfyUI-Minimal")
    )
    
    installer = ComfyUIInstaller(config)
    await installer.install()


async def example_addon_install():
    """Example: Install addon to existing ComfyUI installation."""
    
    from install_addon import AddonInstaller, AddonConfig, VersionRequirement
    
    # Define custom addon installation
    def install_flashattention(installer: AddonInstaller) -> None:
        """Install FlashAttention."""
        installer.install_triton()
        
        # Determine wheel based on versions
        if installer.python_version == "3.12" and installer.torch_version == "2.9":
            wheel_url = (
                "https://huggingface.co/Wildminder/AI-windows-whl/resolve/main/"
                "flash_attn-2.8.3+cu130torch2.9.1cxx11abiTRUE-cp312-cp312-win_amd64.whl"
            )
            installer.installer.pip.install_package(wheel_url)
        else:
            raise RuntimeError("No FlashAttention wheel for current version")
        
        # Create startup script
        startup = installer.base_dir / "Start ComfyUI FlashAttention.bat"
        startup.write_text(
            "@Echo off&&cd /D %~dp0\n"
            "Title ComfyUI with FlashAttention\n"
            ".\\python_embeded\\python.exe -I -W ignore::FutureWarning "
            "ComfyUI\\main.py --windows-standalone-build --use-flash-attention\n"
            "pause\n"
        )
    
    # Configure addon
    config = AddonConfig(
        name="FlashAttention",
        version_requirements=VersionRequirement(
            python=["3.12"],
            torch=["2.7", "2.8", "2.9"],
            cuda=["12.8", "13.0"]
        ),
        install_func=install_flashattention
    )
    
    # Install
    installer = AddonInstaller(Path("ComfyUI-Easy-Install"))
    return installer.install(config)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ComfyUI Installation Examples")
    parser.add_argument(
        "mode",
        choices=["custom", "minimal", "addon"],
        help="Installation mode"
    )
    
    args = parser.parse_args()
    
    try:
        if args.mode == "custom":
            asyncio.run(example_custom_install())
        elif args.mode == "minimal":
            asyncio.run(example_minimal_install())
        elif args.mode == "addon":
            sys.exit(asyncio.run(example_addon_install()))
    except KeyboardInterrupt:
        print("\nCancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
