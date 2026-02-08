"""Package installer classes for pip and uv."""

from pathlib import Path
from typing import Literal

from config import PackageConfig
from utils import logger, run_command


class PyPip:
    """Handles package installation using pip."""
    
    DEFAULT_ARGS = [
        "--no-cache-dir",
        "--no-warn-script-location",
        "--timeout=1000",
        "--retries=10"
    ]
    
    def __init__(self, python_path: Path, default_args: list[str] | None = None):
        """Initialize PyPip.
        
        Args:
            python_path: Path to python.exe
            default_args: Default arguments for pip (uses DEFAULT_ARGS if None)
        """
        self.python_path = Path(python_path)
        self.default_args = default_args or self.DEFAULT_ARGS.copy()
    
    def install_package(
        self,
        package: str,
        *,
        index_url: str | None = None,
        extra_args: list[str] | None = None
    ) -> None:
        """Install a single package.
        
        Args:
            package: Package specification (e.g., "torch==2.9.1")
            index_url: Optional index URL
            extra_args: Additional pip arguments
        """
        cmd = [
            str(self.python_path),
            "-I",
            "-m",
            "pip",
            "install",
            package
        ]
        
        if index_url:
            cmd.extend(["--index-url", index_url])
        
        cmd.extend(self.default_args)
        
        if extra_args:
            cmd.extend(extra_args)
        
        run_command(cmd)
    
    def install_packages(
        self,
        packages: list[str],
        *,
        index_url: str | None = None,
        extra_args: list[str] | None = None
    ) -> None:
        """Install multiple packages in one command.
        
        Args:
            packages: List of package specifications
            index_url: Optional index URL
            extra_args: Additional pip arguments
        """
        cmd = [
            str(self.python_path),
            "-I",
            "-m",
            "pip",
            "install"
        ] + packages
        
        if index_url:
            cmd.extend(["--index-url", index_url])
        
        cmd.extend(self.default_args)
        
        if extra_args:
            cmd.extend(extra_args)
        
        run_command(cmd)
    
    def install_requirements(
        self,
        requirements_file: Path,
        *,
        extra_args: list[str] | None = None
    ) -> None:
        """Install packages from requirements.txt.
        
        Args:
            requirements_file: Path to requirements.txt
            extra_args: Additional pip arguments
        """
        if not requirements_file.exists():
            logger.warning(f"Requirements file not found: {requirements_file}")
            return
        
        # Check if file is empty
        if requirements_file.stat().st_size == 0:
            logger.info(f"Requirements file is empty: {requirements_file}")
            return
        
        cmd = [
            str(self.python_path),
            "-I",
            "-m",
            "pip",
            "install",
            "-r",
            str(requirements_file)
        ]
        
        cmd.extend(self.default_args)
        
        if extra_args:
            cmd.extend(extra_args)
        
        run_command(cmd)
    
    def install_from_config(self, config: PackageConfig) -> None:
        """Install packages from configuration.
        
        Args:
            config: Package configuration
        """
        self.install_packages(
            config.packages,
            index_url=config.index_url,
            extra_args=config.extra_args
        )
    
    def uninstall_package(self, package: str, confirm: bool = False) -> None:
        """Uninstall a package.
        
        Args:
            package: Package name
            confirm: Skip confirmation prompt
        """
        cmd = [
            str(self.python_path),
            "-I",
            "-m",
            "pip",
            "uninstall",
            package
        ]
        
        if not confirm:
            cmd.append("-y")
        
        run_command(cmd, check=False)


class PyUv:
    """Handles package installation using uv (faster alternative to pip)."""
    
    DEFAULT_ARGS = [
        "--no-cache",
        "--link-mode=copy"
    ]
    
    def __init__(self, python_path: Path, default_args: list[str] | None = None):
        """Initialize PyUv.
        
        Args:
            python_path: Path to python.exe
            default_args: Default arguments for uv (uses DEFAULT_ARGS if None)
        """
        self.python_path = Path(python_path)
        self.default_args = default_args or self.DEFAULT_ARGS.copy()
    
    def install_package(
        self,
        package: str,
        *,
        index_url: str | None = None,
        extra_args: list[str] | None = None
    ) -> None:
        """Install a single package.
        
        Args:
            package: Package specification (e.g., "torch==2.9.1")
            index_url: Optional index URL
            extra_args: Additional uv arguments
        """
        cmd = [
            str(self.python_path),
            "-I",
            "-m",
            "uv",
            "pip",
            "install",
            package
        ]
        
        if index_url:
            cmd.extend(["--index-url", index_url])
        
        cmd.extend(self.default_args)
        
        if extra_args:
            cmd.extend(extra_args)
        
        run_command(cmd)
    
    def install_packages(
        self,
        packages: list[str],
        *,
        index_url: str | None = None,
        extra_args: list[str] | None = None
    ) -> None:
        """Install multiple packages in one command.
        
        Args:
            packages: List of package specifications
            index_url: Optional index URL
            extra_args: Additional uv arguments
        """
        cmd = [
            str(self.python_path),
            "-I",
            "-m",
            "uv",
            "pip",
            "install"
        ] + packages
        
        if index_url:
            cmd.extend(["--index-url", index_url])
        
        cmd.extend(self.default_args)
        
        if extra_args:
            cmd.extend(extra_args)
        
        run_command(cmd)
    
    def install_requirements(
        self,
        requirements_file: Path,
        *,
        extra_args: list[str] | None = None
    ) -> None:
        """Install packages from requirements.txt.
        
        Args:
            requirements_file: Path to requirements.txt
            extra_args: Additional uv arguments
        """
        if not requirements_file.exists():
            logger.warning(f"Requirements file not found: {requirements_file}")
            return
        
        # Check if file is empty
        if requirements_file.stat().st_size == 0:
            logger.info(f"Requirements file is empty: {requirements_file}")
            return
        
        cmd = [
            str(self.python_path),
            "-I",
            "-m",
            "uv",
            "pip",
            "install",
            "-r",
            str(requirements_file)
        ]
        
        cmd.extend(self.default_args)
        
        if extra_args:
            cmd.extend(extra_args)
        
        run_command(cmd)
    
    def install_from_config(self, config: PackageConfig) -> None:
        """Install packages from configuration.
        
        Args:
            config: Package configuration
        """
        self.install_packages(
            config.packages,
            index_url=config.index_url,
            extra_args=config.extra_args
        )


class PyInstaller:
    """Facade for package installation using pip or uv."""
    
    def __init__(self, python_path: Path):
        """Initialize PyInstaller.
        
        Args:
            python_path: Path to python.exe
        """
        self.python_path = Path(python_path)
        self.pip = PyPip(python_path)
        self.uv = PyUv(python_path)
    
    def install_package(
        self,
        package: str,
        *,
        use_uv: bool = True,
        index_url: str | None = None,
        extra_args: list[str] | None = None
    ) -> None:
        """Install a package using pip or uv.
        
        Args:
            package: Package specification
            use_uv: Use uv if True, pip if False
            index_url: Optional index URL
            extra_args: Additional arguments
        """
        installer = self.uv if use_uv else self.pip
        installer.install_package(
            package,
            index_url=index_url,
            extra_args=extra_args
        )
    
    def install_packages(
        self,
        packages: list[str],
        *,
        use_uv: bool = True,
        index_url: str | None = None,
        extra_args: list[str] | None = None
    ) -> None:
        """Install multiple packages using pip or uv.
        
        Args:
            packages: List of package specifications
            use_uv: Use uv if True, pip if False
            index_url: Optional index URL
            extra_args: Additional arguments
        """
        installer = self.uv if use_uv else self.pip
        installer.install_packages(
            packages,
            index_url=index_url,
            extra_args=extra_args
        )
    
    def install_requirements(
        self,
        requirements_file: Path,
        *,
        use_uv: bool = True,
        extra_args: list[str] | None = None
    ) -> None:
        """Install from requirements.txt using pip or uv.
        
        Args:
            requirements_file: Path to requirements.txt
            use_uv: Use uv if True, pip if False
            extra_args: Additional arguments
        """
        installer = self.uv if use_uv else self.pip
        installer.install_requirements(
            requirements_file,
            extra_args=extra_args
        )
    
    def install_from_config(
        self,
        config: PackageConfig,
        *,
        use_uv: bool = True
    ) -> None:
        """Install from configuration using pip or uv.
        
        Args:
            config: Package configuration
            use_uv: Use uv if True, pip if False
        """
        installer = self.uv if use_uv else self.pip
        installer.install_from_config(config)
