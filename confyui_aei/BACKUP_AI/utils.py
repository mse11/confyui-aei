"""Utility functions for ComfyUI installation."""

import asyncio
import logging
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

import aiohttp


class ColoredFormatter(logging.Formatter):
    """Colored console log formatter mimicking batch script colors."""
    
    # ANSI color codes matching batch scripts
    COLORS = {
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[91m',    # Red
        'INFO': '\033[92m',     # Green
        'DEBUG': '\033[93m',    # Yellow
        'CRITICAL': '\033[91m', # Red
        'RESET': '\033[0m',
        'BOLD': '\033[1m',
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        color = self.COLORS.get(record.levelname, '')
        reset = self.COLORS['RESET']
        
        # Color the entire message
        record.msg = f"{color}{record.msg}{reset}"
        return super().format(record)


def setup_logger(name: str = __name__) -> logging.Logger:
    """Set up a colored logger."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    formatter = ColoredFormatter('%(message)s')
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    return logger


logger = setup_logger()


def get_python_version(python_path: Path) -> str:
    """Get Python version from executable."""
    try:
        result = subprocess.run(
            [str(python_path), "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        # Output format: "Python 3.12.10"
        version = result.stdout.strip().split()[1]
        # Return major.minor
        parts = version.split('.')
        return f"{parts[0]}.{parts[1]}"
    except Exception as e:
        logger.error(f"Failed to get Python version: {e}")
        return "unknown"


def get_torch_version(python_path: Path) -> str:
    """Get PyTorch version."""
    try:
        result = subprocess.run(
            [str(python_path), "-c", "import torch; print(torch.__version__)"],
            capture_output=True,
            text=True,
            check=True
        )
        version = result.stdout.strip()
        # Return major.minor
        parts = version.split('.')
        return f"{parts[0]}.{parts[1]}"
    except Exception as e:
        logger.error(f"Failed to get Torch version: {e}")
        return "unknown"


def get_cuda_version(python_path: Path) -> str:
    """Get CUDA version from PyTorch."""
    try:
        result = subprocess.run(
            [str(python_path), "-c", 
             "import torch; print(torch.version.cuda if torch.cuda.is_available() else 'Not available')"],
            capture_output=True,
            text=True,
            check=True
        )
        version = result.stdout.strip()
        if version == "Not available":
            return version
        # Return major.minor
        parts = version.split('.')
        return f"{parts[0]}.{parts[1]}"
    except Exception as e:
        logger.error(f"Failed to get CUDA version: {e}")
        return "unknown"


async def download_file(url: str, dest: Path, session: aiohttp.ClientSession | None = None) -> Path:
    """Download file asynchronously with progress indication.
    
    Args:
        url: URL to download from
        dest: Destination path
        session: Optional aiohttp session (creates one if None)
        
    Returns:
        Path to downloaded file
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    
    close_session = session is None
    if session is None:
        session = aiohttp.ClientSession()
    
    try:
        logger.info(f"Downloading {url}")
        async with session.get(url) as response:
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(dest, 'wb') as f:
                async for chunk in response.content.iter_chunked(8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Simple progress indication
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        if downloaded % (1024 * 1024 * 10) < 8192:  # Every 10MB
                            logger.info(f"Progress: {percent:.1f}%")
        
        logger.info(f"Downloaded to {dest}")
        return dest
        
    finally:
        if close_session:
            await session.close()


def extract_zip(zip_path: Path, dest: Path) -> None:
    """Extract zip archive to destination."""
    logger.info(f"Extracting {zip_path.name} to {dest}")
    dest.mkdir(parents=True, exist_ok=True)
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(dest)
    
    logger.info(f"Extracted to {dest}")


def cleanup_temp_folders(base_path: Path, pattern: str) -> None:
    """Remove temporary folders matching pattern.
    
    Args:
        base_path: Base directory to search in
        pattern: Glob pattern to match (e.g., "~*")
    """
    if not base_path.exists():
        return
        
    for folder in base_path.glob(pattern):
        if folder.is_dir():
            logger.info(f"Removing temp folder: {folder}")
            try:
                import shutil
                shutil.rmtree(folder)
            except Exception as e:
                logger.warning(f"Failed to remove {folder}: {e}")


def run_command(
    cmd: list[str],
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    check: bool = True
) -> subprocess.CompletedProcess:
    """Run a command and return the result.
    
    Args:
        cmd: Command and arguments as list
        cwd: Working directory
        env: Environment variables
        check: Raise exception on non-zero exit
        
    Returns:
        CompletedProcess instance
    """
    logger.info(f"Running: {' '.join(cmd)}")
    
    result = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False
    )
    
    if result.stdout:
        logger.debug(result.stdout)
    if result.stderr:
        logger.warning(result.stderr)
    
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode,
            cmd,
            result.stdout,
            result.stderr
        )
    
    return result


async def run_parallel(tasks: list[asyncio.Task]) -> list[Any]:
    """Run multiple async tasks in parallel.
    
    Args:
        tasks: List of asyncio tasks
        
    Returns:
        List of results
    """
    return await asyncio.gather(*tasks, return_exceptions=True)
