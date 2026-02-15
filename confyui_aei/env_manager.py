"""Python embedded environment manager.

Downloads and bootstraps an embedded Python environment with pip and uv,
provides package installation via pip and uv-pip, clones git repos,
runs arbitrary shell commands, and checks Python/Torch/CUDA versions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from nbaio.util import AioUtils
from rich.console import Console

from .config import GitCloneTarget, PipPackageGroup, PythonEmbedConfig, ShellCommand, SupportedVersions, UvPackageGroup

console = Console()


class PythonEnvManager:
    """Download, extract, bootstrap an embedded Python env, and install packages."""

    def __init__(self, config: PythonEmbedConfig, base_dir: Path) -> None:
        self.config = config
        self.base_dir = Path(base_dir)
        self.embed_dir = self.base_dir / "python_embeded"

    @property
    def python_exe(self) -> Path:
        return self.embed_dir / "python.exe"

    # ================================================================
    # Environment setup
    # ================================================================

    async def setup(self, ui_enabled: bool = True) -> Path:
        """Download embedded Python, extract, write pth, bootstrap pip + uv.

        Returns:
            Path to the ``python.exe`` inside the embedded environment.
        """
        self.embed_dir.mkdir(parents=True, exist_ok=True)

        archive_path = self.embed_dir / self.config.archive_name

        # 1. Download embedded Python archive
        console.print(f"[green]::: Downloading [yellow]{self.config.archive_name}[/]")
        ok = await AioUtils.download_file(
            self.config.download_url,
            archive_path,
            ui_enabled=ui_enabled,
        )
        if not ok:
            raise RuntimeError(f"Failed to download {self.config.download_url}")

        # 2. Extract archive into embed_dir
        console.print(f"[green]::: Extracting [yellow]{self.config.archive_name}[/]")
        ok = await AioUtils.extract_zip(
            archive_path,
            self.embed_dir,
            remove_after=True,
            ui_enabled=ui_enabled,
        )
        if not ok:
            raise RuntimeError(f"Failed to extract {archive_path}")

        # 3. Write ._pth file
        pth_file = self.embed_dir / "python312._pth"
        pth_file.write_text("\n".join(self.config.pth_lines) + "\n", encoding="utf-8")
        console.print(f"[green]::: Wrote [yellow]{pth_file.name}[/]")

        # 4. Download and run get-pip.py
        get_pip_path = self.embed_dir / "get-pip.py"
        await AioUtils.download_file(
            "https://bootstrap.pypa.io/get-pip.py",
            get_pip_path,
            ui_enabled=ui_enabled,
        )

        console.print("[green]::: Bootstrapping [yellow]pip[/]")
        rc, stdout, stderr = await AioUtils.shell_cmd(
            [str(self.python_exe), "-I", str(get_pip_path),
             "--no-cache-dir", "--no-warn-script-location",
             "--timeout=1000", "--retries", "10"],
            cwd=self.embed_dir,
            capture_output=True,
            ui_enabled=ui_enabled,
        )
        if rc != 0:
            raise RuntimeError(f"pip bootstrap failed (rc={rc}): {stderr}")

        # 5. Install uv
        console.print("[green]::: Installing [yellow]uv[/]")
        rc, stdout, stderr = await AioUtils.shell_cmd_py_pip(
            self.python_exe,
            ["uv==0.9.7"],
            extra_args=AioUtils.SHELL_CMD_PY_PIP_ARGS_confyui,
            ui_enabled=ui_enabled,
        )
        if rc != 0:
            raise RuntimeError(f"uv install failed (rc={rc}): {stderr}")

        console.print("[green]::: Embedded Python environment ready[/]")
        return self.python_exe

    # ================================================================
    # pip install
    # ================================================================

    async def install_pip(
        self,
        group: PipPackageGroup,
        ui_enabled: bool = True,
    ) -> tuple[int, str, str]:
        """Install a group of packages via ``pip install``.

        Handles ``force_reinstall`` and ``no_deps`` flags from the config.
        """
        packages = list(group.packages)

        extra = list(group.extra_args)
        if group.force_reinstall:
            extra.append("--force-reinstall")
        if group.no_deps:
            extra.append("--no-deps")

        console.print(f"[green]::: pip install [yellow]{group.name}[/]")

        return await AioUtils.shell_cmd_py_pip(
            self.python_exe,
            packages,
            extra_args=extra or AioUtils.SHELL_CMD_PY_PIP_ARGS_confyui,
            ui_enabled=ui_enabled,
        )

    async def install_pip_groups(
        self,
        groups: list[PipPackageGroup],
        ui_enabled: bool = True,
    ) -> list[tuple[int, str, str]]:
        """Install multiple pip package groups sequentially."""
        results: list[tuple[int, str, str]] = []
        for group in groups:
            result = await self.install_pip(group, ui_enabled=ui_enabled)
            results.append(result)
        return results

    # ================================================================
    # uv pip install
    # ================================================================

    async def install_uv_pip(
        self,
        group: UvPackageGroup,
        ui_enabled: bool = True,
    ) -> tuple[int, str, str]:
        """Install a group of packages via ``uv pip install``."""
        console.print(f"[green]::: uv pip install [yellow]{group.name}[/]")

        return await AioUtils.shell_cmd_py_uv_pip(
            self.python_exe,
            group.packages,
            extra_args=group.extra_args or AioUtils.SHELL_CMD_PY_UV_PIP_ARGS_confyui,
            ui_enabled=ui_enabled,
        )

    async def install_uv_pip_groups(
        self,
        groups: list[UvPackageGroup],
        ui_enabled: bool = True,
    ) -> list[tuple[int, str, str]]:
        """Install multiple uv-pip package groups sequentially."""
        results: list[tuple[int, str, str]] = []
        for group in groups:
            result = await self.install_uv_pip(group, ui_enabled=ui_enabled)
            results.append(result)
        return results

    # ================================================================
    # Git clone
    # ================================================================

    async def clone_all(
        self,
        targets: list[GitCloneTarget],
        cwd: Optional[Path] = None,
        ui_enabled: bool = True,
        skip_lfs: bool = True,
    ) -> list[tuple[int, str, str]]:
        """Clone all targets concurrently using ``git clone``.

        Args:
            targets: List of GitCloneTarget configs.
            cwd: Working directory for the clone commands.
            ui_enabled: Whether to show progress output.
            skip_lfs: Whether to skip Git LFS files.

        Returns:
            List of (return_code, stdout, stderr) for each clone.
        """
        if not targets:
            return []

        clones = [(t.url, t.dest_dir) for t in targets]

        console.print(f"[green]::: Cloning [yellow]{len(targets)}[/green] repositories[/]")
        for t in targets:
            console.print(f"  [dim]→ {t.url}  →  {t.dest_dir}[/]")

        return await AioUtils.shell_cmds_git_clone(
            clones,
            cwd=cwd,
            ui_enabled=ui_enabled,
            skip_lfs=skip_lfs,
        )

    # ================================================================
    # Shell commands
    # ================================================================

    async def shell_run(
        self,
        cmd: ShellCommand,
        ui_enabled: bool = True,
        capture_output: bool = True,
    ) -> tuple[int, str, str]:
        """Run a single shell command.

        Args:
            cmd: The ShellCommand config to run.
            ui_enabled: Whether to show output.
            capture_output: Whether to capture stdout/stderr.

        Returns:
            Tuple of (return_code, stdout, stderr).
        """
        console.print(f"[green]::: Running [yellow]{cmd.command}[/]")

        return await AioUtils.shell_cmd(
            cmd.command,
            cwd=cmd.cwd,
            capture_output=capture_output,
            ui_enabled=ui_enabled,
        )

    async def shell_run_all(
        self,
        commands: list[ShellCommand],
        ui_enabled: bool = True,
        capture_output: bool = True,
    ) -> list[tuple[int, str, str]]:
        """Run multiple shell commands concurrently.

        Args:
            commands: List of ShellCommand configs.
            ui_enabled: Whether to show output.
            capture_output: Whether to capture stdout/stderr.

        Returns:
            List of (return_code, stdout, stderr) tuples.
        """
        if not commands:
            return []

        raw_commands = [c.command for c in commands]
        # Use the cwd of the first command — for concurrency each
        # command should share the same cwd or use absolute paths.
        cwd = commands[0].cwd if commands else None

        return await AioUtils.shell_cmds(
            raw_commands,
            cwd=cwd,
            capture_output=capture_output,
            ui_enabled=ui_enabled,
        )

    # ================================================================
    # Version checking
    # ================================================================

    async def get_versions(self, ui_enabled: bool = True) -> dict[str, str]:
        """Query the embedded Python for version info.

        Returns:
            Dictionary with keys ``python``, ``torch``, ``cuda`` mapping to
            short version strings like ``"3.12"``, ``"2.9"``, ``"13.0"``.
        """
        versions: dict[str, str] = {}

        # Python version (e.g. "3.12")
        rc, stdout, _ = await AioUtils.shell_cmd(
            [str(self.python_exe), "--version"],
            capture_output=True,
            ui_enabled=False,
        )
        if rc == 0 and stdout.strip():
            # "Python 3.12.10" -> "3.12"
            parts = stdout.strip().split()[-1].split(".")
            versions["python"] = f"{parts[0]}.{parts[1]}"

        # Torch version (e.g. "2.9")
        rc, stdout, _ = await AioUtils.shell_cmd(
            [str(self.python_exe), "-c",
             "import torch; print(torch.__version__)"],
            capture_output=True,
            ui_enabled=False,
        )
        if rc == 0 and stdout.strip():
            parts = stdout.strip().split(".")
            versions["torch"] = f"{parts[0]}.{parts[1]}"

        # CUDA version (e.g. "13.0")
        rc, stdout, _ = await AioUtils.shell_cmd(
            [str(self.python_exe), "-c",
             "import torch; print(torch.version.cuda if torch.cuda.is_available() else 'N/A')"],
            capture_output=True,
            ui_enabled=False,
        )
        if rc == 0 and stdout.strip() and stdout.strip() != "N/A":
            parts = stdout.strip().split(".")
            versions["cuda"] = f"{parts[0]}.{parts[1]}"
        else:
            versions["cuda"] = "N/A"

        if ui_enabled:
            console.print(f"[green]::: Python Version: [yellow]{versions.get('python', '?')}[/]")
            console.print(f"[green]::: Torch  Version: [yellow]{versions.get('torch', '?')}[/]")
            console.print(f"[green]::: CUDA   Version: [yellow]{versions.get('cuda', '?')}[/]")

        return versions

    @staticmethod
    def check_support(
        versions: dict[str, str],
        supported: SupportedVersions,
    ) -> list[str]:
        """Check if detected versions are supported.

        Args:
            versions: Dict from ``get_versions()``.
            supported: SupportedVersions config.

        Returns:
            List of warning messages. Empty list means all supported.
        """
        warnings: list[str] = []

        py = versions.get("python", "")
        if py and py not in supported.python:
            warnings.append(
                f"Python {py} is not supported. Supported: {', '.join(supported.python)}"
            )

        torch = versions.get("torch", "")
        if torch and torch not in supported.torch:
            warnings.append(
                f"Torch {torch} is not supported. Supported: {', '.join(supported.torch)}"
            )

        cuda = versions.get("cuda", "")
        if cuda and cuda != "N/A" and cuda not in supported.cuda:
            warnings.append(
                f"CUDA {cuda} is not supported. Supported: {', '.join(supported.cuda)}"
            )

        return warnings
