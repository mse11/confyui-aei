"""Generic addon installer - Python version of batch addon scripts."""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from package_installer import PyInstaller, PyPip
from utils import get_cuda_version, get_python_version, get_torch_version, logger


@dataclass
class VersionRequirement:
    """Version requirement specification."""
    
    python: list[str] | None = None
    torch: list[str] | None = None
    cuda: list[str] | None = None


@dataclass
class AddonConfig:
    """Configuration for an addon installation."""
    
    name: str
    version_requirements: VersionRequirement
    install_func: Callable[["AddonInstaller"], None]


class AddonInstaller:
    """Generic installer for ComfyUI addons."""
    
    def __init__(self, base_dir: Path):
        """Initialize addon installer.
        
        Args:
            base_dir: Base ComfyUI installation directory
        """
        self.base_dir = Path(base_dir)
        self.python_path = self.base_dir / "python_embeded" / "python.exe"
        
        if not self.python_path.exists():
            raise RuntimeError(f"Python not found at {self.python_path}")
        
        self.installer = PyInstaller(self.python_path)
        
        # Detect versions
        self.python_version = get_python_version(self.python_path)
        self.torch_version = get_torch_version(self.python_path)
        self.cuda_version = get_cuda_version(self.python_path)
    
    def check_versions(self, requirements: VersionRequirement) -> bool:
        """Check if current versions meet requirements.
        
        Args:
            requirements: Version requirements
            
        Returns:
            True if all requirements are met
        """
        logger.info("Checking versions")
        logger.info(f"Python Version: {self.python_version}")
        logger.info(f"Torch Version: {self.torch_version}")
        logger.info(f"CUDA Version: {self.cuda_version}")
        logger.info("")
        
        warnings = []
        
        if requirements.python and self.python_version not in requirements.python:
            warnings.append(
                f"Python {self.python_version} is not supported. "
                f"Supported versions: {', '.join(requirements.python)}"
            )
        
        if requirements.torch and self.torch_version not in requirements.torch:
            warnings.append(
                f"Torch {self.torch_version} is not supported. "
                f"Supported versions: {', '.join(requirements.torch)}"
            )
        
        if requirements.cuda and self.cuda_version not in requirements.cuda:
            warnings.append(
                f"CUDA {self.cuda_version} is not supported. "
                f"Supported versions: {', '.join(requirements.cuda)}"
            )
        
        if warnings:
            for warning in warnings:
                logger.warning(f"WARNING: {warning}")
            logger.info("")
            return False
        
        logger.info("All versions are supported!")
        logger.info("")
        return True
    
    def install_triton(self) -> None:
        """Install Triton based on Torch version."""
        logger.info("Installing Triton")
        
        triton_pkg = None
        if self.torch_version == "2.9":
            triton_pkg = "triton-windows<3.6"
        elif self.torch_version == "2.8":
            triton_pkg = "triton-windows==3.4.0.post20"
        elif self.torch_version == "2.7":
            triton_pkg = "triton-windows==3.3.1.post19"
        
        if triton_pkg:
            self.installer.pip.install_package(
                triton_pkg,
                extra_args=["--upgrade", "--force-reinstall"]
            )
        else:
            logger.warning(f"No Triton package defined for Torch {self.torch_version}")
    
    def cleanup_temp_folders(self) -> None:
        """Cleanup temporary folders."""
        from utils import cleanup_temp_folders
        
        site_packages = self.base_dir / "python_embeded" / "Lib" / "site-packages"
        cleanup_temp_folders(site_packages, "~*")
    
    def install(self, config: AddonConfig) -> int:
        """Install addon.
        
        Args:
            config: Addon configuration
            
        Returns:
            Exit code (0 = success, 1 = failure)
        """
        logger.info("=" * 60)
        logger.info(f"Installing {config.name}")
        logger.info("=" * 60)
        logger.info("")
        
        # Check version requirements
        if not self.check_versions(config.version_requirements):
            logger.error("Version requirements not met")
            return 1
        
        try:
            # Cleanup temp folders
            self.cleanup_temp_folders()
            
            # Run addon-specific installation
            config.install_func(self)
            
            logger.info("")
            logger.info("=" * 60)
            logger.info(f"{config.name} Installation Complete")
            logger.info("=" * 60)
            
            return 0
            
        except Exception as e:
            logger.error(f"Installation failed: {e}")
            return 1


# Example: SageAttention installer
def install_sageattention(installer: AddonInstaller) -> None:
    """Install SageAttention addon."""
    # Install Triton
    installer.install_triton()
    
    # Determine wheel URL based on versions
    wheel_url = None
    if installer.torch_version == "2.7" and installer.cuda_version == "12.8":
        wheel_url = (
            "https://github.com/woct0rdho/SageAttention/releases/download/"
            "v2.2.0-windows.post3/sageattention-2.2.0+cu128torch2.7.1.post3-cp39-abi3-win_amd64.whl"
        )
    elif installer.torch_version == "2.8" and installer.cuda_version == "12.8":
        wheel_url = (
            "https://github.com/woct0rdho/SageAttention/releases/download/"
            "v2.2.0-windows.post3/sageattention-2.2.0+cu128torch2.8.0.post3-cp39-abi3-win_amd64.whl"
        )
    elif installer.torch_version == "2.9" and installer.cuda_version == "12.8":
        wheel_url = (
            "https://github.com/woct0rdho/SageAttention/releases/download/"
            "v2.2.0-windows.post4/sageattention-2.2.0+cu128torch2.9.0andhigher.post4-cp39-abi3-win_amd64.whl"
        )
    elif installer.torch_version == "2.9" and installer.cuda_version == "13.0":
        wheel_url = (
            "https://github.com/woct0rdho/SageAttention/releases/download/"
            "v2.2.0-windows.post4/sageattention-2.2.0+cu130torch2.9.0andhigher.post4-cp39-abi3-win_amd64.whl"
        )
    
    if not wheel_url:
        raise RuntimeError(
            f"No SageAttention wheel available for Torch {installer.torch_version} "
            f"and CUDA {installer.cuda_version}"
        )
    
    # Install SageAttention
    logger.info("Installing SageAttention")
    installer.installer.pip.install_package(
        wheel_url,
        extra_args=["--upgrade", "--force-reinstall"]
    )
    
    # Create startup script
    startup_script = installer.base_dir / "Start ComfyUI SageAttention.bat"
    if not startup_script.exists():
        logger.info("Creating Start ComfyUI SageAttention.bat")
        content = """@Echo off&&cd /D %~dp0
Title ComfyUI-Easy-Install with SageAttention
.\\python_embeded\\python.exe -I -W ignore::FutureWarning ComfyUI\\main.py --windows-standalone-build --use-sage-attention
pause
"""
        startup_script.write_text(content)


# Example usage
if __name__ == "__main__":
    base_dir = Path("ComfyUI-Easy-Install")
    
    if not base_dir.exists():
        logger.error(f"Installation directory not found: {base_dir}")
        logger.error("Please run install_comfyui.py first")
        sys.exit(1)
    
    # SageAttention configuration
    sageattention_config = AddonConfig(
        name="SageAttention",
        version_requirements=VersionRequirement(
            python=["3.11", "3.12"],
            torch=["2.7", "2.8", "2.9"],
            cuda=["12.8", "13.0"]
        ),
        install_func=install_sageattention
    )
    
    # Install
    installer = AddonInstaller(base_dir)
    exit_code = installer.install(sageattention_config)
    sys.exit(exit_code)
