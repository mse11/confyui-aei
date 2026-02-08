"""Main ComfyUI installation script - Python version of ComfyUI-Easy-Install.bat."""

import asyncio
import sys
from pathlib import Path

from config import (
    DEFAULT_CUSTOM_NODES,
    DEFAULT_PYTHON_VERSION,
    DEFAULT_TORCH_2_9_CU130,
    GitRepoConfig,
    InstallConfig,
    PackageConfig,
)
from git_manager import Git
from package_installer import PyInstaller
from pyembed import PyEmbeder
from utils import cleanup_temp_folders, logger


class ComfyUIInstaller:
    """Main installer for ComfyUI."""
    
    def __init__(self, config: InstallConfig):
        """Initialize installer.
        
        Args:
            config: Installation configuration
        """
        self.config = config
        self.base_dir = config.install_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        self.embedder = PyEmbeder(self.base_dir)
        self.installer: PyInstaller | None = None
        self.git: Git | None = None
    
    async def install(self) -> None:
        """Run full installation."""
        logger.info("=" * 60)
        logger.info("ComfyUI Easy Install - Python Version")
        logger.info("=" * 60)
        
        try:
            # Step 1: Setup Python embedded environment
            await self.setup_python()
            
            # Step 2: Install PyTorch
            await self.install_pytorch()
            
            # Step 3: Clone ComfyUI
            await self.clone_comfyui()
            
            # Step 4: Install ComfyUI requirements
            await self.install_comfyui_requirements()
            
            # Step 5: Install base packages
            await self.install_base_packages()
            
            # Step 6: Clone custom nodes
            await self.install_custom_nodes()
            
            # Step 7: Create startup scripts
            self.create_startup_scripts()
            
            # Step 8: Cleanup
            self.cleanup()
            
            logger.info("=" * 60)
            logger.info("Installation Complete!")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Installation failed: {e}")
            raise
    
    async def setup_python(self) -> None:
        """Setup Python embedded environment."""
        logger.info("\n" + "=" * 60)
        logger.info("Setting up Python")
        logger.info("=" * 60)
        
        python_path = await self.embedder.setup(self.config.python_version)
        
        # Verify installation
        if not self.embedder.verify_installation():
            raise RuntimeError("Python installation verification failed")
        
        # Initialize installer and git manager
        self.installer = PyInstaller(python_path)
        custom_nodes_dir = self.base_dir / "ComfyUI" / "custom_nodes"
        self.git = Git(python_path, custom_nodes_dir)
    
    async def install_pytorch(self) -> None:
        """Install PyTorch."""
        logger.info("\n" + "=" * 60)
        logger.info("Installing PyTorch")
        logger.info("=" * 60)
        
        if not self.installer:
            raise RuntimeError("Installer not initialized")
        
        # Use pip for PyTorch (more reliable than uv for large packages)
        self.installer.install_from_config(
            self.config.torch_packages,
            use_uv=False
        )
    
    async def clone_comfyui(self) -> None:
        """Clone ComfyUI repository."""
        logger.info("\n" + "=" * 60)
        logger.info("Cloning ComfyUI")
        logger.info("=" * 60)
        
        comfyui_dir = self.base_dir / "ComfyUI"
        
        if comfyui_dir.exists():
            logger.info("ComfyUI already exists")
            return
        
        # Clone to base directory (not custom_nodes)
        from utils import run_command
        await asyncio.to_thread(
            run_command,
            ["git", "clone", "https://github.com/Comfy-Org/ComfyUI", "ComfyUI"],
            cwd=self.base_dir
        )
    
    async def install_comfyui_requirements(self) -> None:
        """Install ComfyUI requirements."""
        logger.info("\n" + "=" * 60)
        logger.info("Installing ComfyUI requirements")
        logger.info("=" * 60)
        
        if not self.installer:
            raise RuntimeError("Installer not initialized")
        
        requirements = self.base_dir / "ComfyUI" / "requirements.txt"
        
        # Install specific av version first (compatibility fix)
        logger.info("Installing av==16.0.1")
        self.installer.install_package("av==16.0.1", use_uv=True)
        
        # Install requirements
        self.installer.install_requirements(requirements, use_uv=True)
    
    async def install_base_packages(self) -> None:
        """Install base packages."""
        logger.info("\n" + "=" * 60)
        logger.info("Installing base packages")
        logger.info("=" * 60)
        
        if not self.installer:
            raise RuntimeError("Installer not initialized")
        
        base_packages = [
            "scikit-build-core",
            "onnxruntime-gpu",
            "onnx",
            "flet",
            "stringzilla==3.12.6",
            "transformers==4.57.6",
        ]
        
        for package in base_packages:
            logger.info(f"Installing {package}")
            self.installer.install_package(package, use_uv=True)
        
        # Install llama-cpp-python wheel
        logger.info("Installing llama-cpp-python")
        llama_wheel = (
            "https://github.com/JamePeng/llama-cpp-python/releases/download/"
            "v0.3.18-cu130-Basic-win-20251223/llama_cpp_python-0.3.18-cp312-cp312-win_amd64.whl"
        )
        self.installer.install_package(llama_wheel, use_uv=True)
        
        # Install Triton
        logger.info("Installing triton-windows")
        self.installer.pip.install_package(
            "triton-windows",
            extra_args=["--upgrade", "--force-reinstall", "triton-windows<3.6"]
        )
    
    async def install_custom_nodes(self) -> None:
        """Install custom nodes."""
        logger.info("\n" + "=" * 60)
        logger.info("Installing custom nodes")
        logger.info("=" * 60)
        
        if not self.git:
            raise RuntimeError("Git manager not initialized")
        
        # Create .disabled folder
        disabled_dir = self.base_dir / "ComfyUI" / "custom_nodes" / ".disabled"
        disabled_dir.mkdir(parents=True, exist_ok=True)
        
        # Clone custom nodes in parallel
        await self.git.clone_multiple(
            self.config.custom_nodes,
            skip_lfs=True,
            install_deps=True,
            max_parallel=5
        )
    
    def create_startup_scripts(self) -> None:
        """Create startup batch scripts."""
        logger.info("\n" + "=" * 60)
        logger.info("Creating startup scripts")
        logger.info("=" * 60)
        
        # Start ComfyUI.bat
        startup_script = self.base_dir / "Start ComfyUI.bat"
        startup_content = """@Echo off&&cd /D %~dp0
Title ComfyUI-Easy-Install
.\\python_embeded\\python.exe -I -W ignore::FutureWarning ComfyUI\\main.py --windows-standalone-build

echo.
echo If you see this and ComfyUI did not start, [92mtry updating your Nvidia drivers.[0m
echo If you get a c10.dll error, [92minstall VC Redist: https://aka.ms/vc14/vc_redist.x64.exe[0m
echo.
echo Press any key to exit&Pause>nul
"""
        startup_script.write_text(startup_content)
        logger.info(f"Created {startup_script.name}")
        
        # Update ComfyUI.bat
        update_script = self.base_dir / "Update ComfyUI.bat"
        update_content = """@echo off&&cd /D %~dp0
Title ComfyUI-Update by ivo

echo [92m::::::::::::::: Updating ComfyUI :::::::::::::::[0m
echo.
cd .\\ComfyUI&&git.exe checkout master -q&&cd ..\\
cd .\\update&&call .\\update_comfyui.bat nopause&&cd ..\\
echo.
echo [92m:::::::::::: Done. Starting ComfyUI ::::::::::::[0m
echo.
call "Start ComfyUI.bat"
"""
        update_script.write_text(update_content)
        logger.info(f"Created {update_script.name}")
    
    def cleanup(self) -> None:
        """Cleanup temporary files."""
        logger.info("\n" + "=" * 60)
        logger.info("Cleaning up")
        logger.info("=" * 60)
        
        # Remove ~* folders from site-packages
        site_packages = self.base_dir / "python_embeded" / "Lib" / "site-packages"
        cleanup_temp_folders(site_packages, "~*")


async def main():
    """Main entry point."""
    # Configure installation
    config = InstallConfig(
        python_version=DEFAULT_PYTHON_VERSION,
        torch_packages=DEFAULT_TORCH_2_9_CU130,
        custom_nodes=DEFAULT_CUSTOM_NODES,
        install_dir=Path("ComfyUI-Easy-Install")
    )
    
    # Run installation
    installer = ComfyUIInstaller(config)
    await installer.install()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nInstallation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\nInstallation failed: {e}")
        sys.exit(1)
