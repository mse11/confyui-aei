"""PyEmbeder - Python embedded environment management."""

import asyncio
import os
from pathlib import Path

import aiohttp

from config import PythonVersionConfig
from utils import download_file, extract_zip, logger, run_command


class PyEmbeder:
    """Manages Python embedded environments for portable installations."""
    
    def __init__(self, base_dir: Path):
        """Initialize PyEmbeder.
        
        Args:
            base_dir: Base directory for the installation
        """
        self.base_dir = Path(base_dir)
        self.python_dir = self.base_dir / "python_embeded"
        self.python_exe = self.python_dir / "python.exe"
    
    async def setup(self, config: PythonVersionConfig) -> Path:
        """Set up Python embedded environment.
        
        Args:
            config: Python version configuration
            
        Returns:
            Path to python.exe
        """
        if self.python_exe.exists():
            logger.info(f"Python already installed at {self.python_exe}")
            return self.python_exe
        
        logger.info(f"Setting up Python {config.version}")
        
        # Download Python embedded
        zip_path = await self.download_python(config)
        
        # Extract
        self.extract_python(zip_path)
        
        # Configure
        await self.configure_environment()
        
        # Cleanup
        zip_path.unlink()
        
        logger.info(f"Python {config.version} setup complete")
        return self.python_exe
    
    async def download_python(self, config: PythonVersionConfig) -> Path:
        """Download Python embedded distribution.
        
        Args:
            config: Python version configuration
            
        Returns:
            Path to downloaded zip file
        """
        url = config.download_url_computed
        zip_path = self.python_dir / f"python-{config.version}-embed-amd64.zip"
        
        async with aiohttp.ClientSession() as session:
            await download_file(url, zip_path, session)
        
        return zip_path
    
    def extract_python(self, zip_path: Path) -> None:
        """Extract Python embedded zip.
        
        Args:
            zip_path: Path to Python zip file
        """
        extract_zip(zip_path, self.python_dir)
    
    async def configure_environment(self) -> None:
        """Configure Python embedded environment (paths, pip, uv)."""
        # Configure python312._pth for proper imports
        pth_file = self.python_dir / "python312._pth"
        pth_content = [
            "../ComfyUI",
            "python312.zip",
            ".",
            "Lib/site-packages",
            "Lib",
            "Scripts",
            "# import site"
        ]
        
        logger.info("Configuring Python paths")
        pth_file.write_text('\n'.join(pth_content))
        
        # Download get-pip.py
        logger.info("Installing pip")
        get_pip_url = "https://bootstrap.pypa.io/get-pip.py"
        get_pip_path = self.python_dir / "get-pip.py"
        
        async with aiohttp.ClientSession() as session:
            await download_file(get_pip_url, get_pip_path, session)
        
        # Install pip
        run_command(
            [str(self.python_exe), "-I", str(get_pip_path)],
            cwd=self.python_dir
        )
        
        # Install uv
        logger.info("Installing uv")
        run_command(
            [str(self.python_exe), "-I", "-m", "pip", "install", "uv==0.9.7",
             "--no-cache-dir", "--no-warn-script-location", "--timeout=1000", "--retries=10"]
        )
        
        # Cleanup
        get_pip_path.unlink()
    
    def get_python_path(self) -> Path:
        """Get path to python.exe.
        
        Returns:
            Path to python.exe
        """
        return self.python_exe
    
    def verify_installation(self) -> bool:
        """Verify Python installation is working.
        
        Returns:
            True if Python is properly installed
        """
        if not self.python_exe.exists():
            return False
        
        try:
            result = run_command(
                [str(self.python_exe), "--version"],
                check=True
            )
            logger.info(f"Python verified: {result.stdout.strip()}")
            return True
        except Exception as e:
            logger.error(f"Python verification failed: {e}")
            return False
