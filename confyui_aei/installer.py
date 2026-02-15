"""Main orchestrator for ComfyUI Easy Install.

Wires together PythonEnvManager and the configuration layer.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from nbaio.util import AioUtils
from rich.console import Console

from .config import (
    AddonConfig,
    GitCloneTarget,
    InstallerConfig,
    PipPackageGroup,
    PythonEmbedConfig,
    UvPackageGroup,
    WheelMatrix,
)
from .env_manager import PythonEnvManager

console = Console()


class ComfyUIInstaller:
    """Orchestrates a full ComfyUI install or individual add-on installs."""

    def __init__(self, config: InstallerConfig, base_dir: Path) -> None:
        self.config = config
        self.base_dir = Path(base_dir)

    def _make_env_mgr(self) -> PythonEnvManager:
        """Create a PythonEnvManager bound to the current base_dir."""
        return PythonEnvManager(self.config.python_embed, self.base_dir)

    # ================================================================
    # Full install (mirrors ComfyUI-Easy-Install.bat)
    # ================================================================

    async def run_full_install(self, ui_enabled: bool = True) -> None:
        """Execute the full installation pipeline."""
        console.print("[bold green]=== ComfyUI Easy Install ===[/]")

        # 1. Setup embedded Python first (needed for clone_all)
        env_mgr = self._make_env_mgr()

        # 2. Clone ComfyUI
        console.print("[green]::: Installing [yellow]ComfyUI[/]")
        comfyui_target = GitCloneTarget(
            url=self.config.comfyui_repo_url,
            dest_dir=str(self.base_dir / "ComfyUI"),
        )
        await env_mgr.clone_all([comfyui_target], ui_enabled=ui_enabled)

        # 3. Setup embedded Python
        python_exe = await env_mgr.setup(ui_enabled=ui_enabled)

        # 4. Install Torch via pip
        console.print("[green]::: Installing [yellow]Torch[/]")
        await env_mgr.install_pip_groups(
            self.config.pip_groups, ui_enabled=ui_enabled
        )

        # 5. Install uv-pip packages (pygit2, av, requirements, pre-install)
        console.print("[green]::: Installing [yellow]uv-pip packages[/]")
        await env_mgr.install_uv_pip_groups(
            self.config.uv_groups, ui_enabled=ui_enabled
        )

        # 6. Clone custom nodes
        console.print("[green]::: Cloning [yellow]custom nodes[/]")
        custom_nodes_dir = self.base_dir / "ComfyUI" / "custom_nodes"
        node_targets = []
        for t in self.config.git_clones:
            node_targets.append(
                GitCloneTarget(
                    url=t.url,
                    dest_dir=str(custom_nodes_dir / t.dest_dir),
                )
            )
        results = await env_mgr.clone_all(node_targets, ui_enabled=ui_enabled)

        # 7. Install requirements.txt for each cloned node
        await self._install_node_requirements(
            env_mgr, custom_nodes_dir, ui_enabled
        )

        # 8. Create .disabled directory
        disabled_dir = custom_nodes_dir / ".disabled"
        disabled_dir.mkdir(parents=True, exist_ok=True)

        console.print("[bold green]=== Installation Complete ===[/]")

    async def _install_node_requirements(
        self,
        env_mgr: PythonEnvManager,
        custom_nodes_dir: Path,
        ui_enabled: bool,
    ) -> None:
        """Install requirements.txt and run install.py for each cloned node."""
        for node_dir in custom_nodes_dir.iterdir():
            if not node_dir.is_dir() or node_dir.name.startswith("."):
                continue

            req_file = node_dir / "requirements.txt"
            if req_file.exists() and req_file.stat().st_size > 0:
                group = UvPackageGroup(
                    name=f"{node_dir.name}-requirements",
                    packages=["-r", str(req_file)],
                    extra_args=["--no-cache", "--link-mode=copy"],
                )
                await env_mgr.install_uv_pip(group, ui_enabled=ui_enabled)

            install_py = node_dir / "install.py"
            if install_py.exists() and install_py.stat().st_size > 0:
                console.print(f"[green]::: Running install.py for [yellow]{node_dir.name}[/]")
                await AioUtils.shell_cmd(
                    [str(env_mgr.python_exe), "-I", str(install_py)],
                    capture_output=True,
                    ui_enabled=ui_enabled,
                )

    # ================================================================
    # Add-on install (mirrors per-addon .bat files)
    # ================================================================

    async def run_addon(
        self,
        addon: AddonConfig,
        ui_enabled: bool = True,
    ) -> None:
        """Install a single add-on.

        Steps:
          1. Check Python/Torch/CUDA version support.
          2. Run pre-install pip groups (e.g. Triton).
          3. Clone git repos if any.
          4. Resolve wheel from version matrix.
          5. Install pip groups (with resolved wheel URL).
          6. Run shell commands.
        """
        env_mgr = self._make_env_mgr()
        if not env_mgr.python_exe.exists():
            raise RuntimeError(
                f"Embedded Python not found at {env_mgr.python_exe}. "
                "Run full install first."
            )

        console.print(f"[bold green]=== Installing {addon.name} ===[/]")

        # 1. Version check
        versions = await env_mgr.get_versions(ui_enabled=ui_enabled)
        warnings = env_mgr.check_support(versions, addon.supported_versions)
        if warnings:
            for w in warnings:
                console.print(f"[bold yellow]WARNING: [red]{w}[/]")
            raise RuntimeError(
                f"Version check failed for {addon.name}. "
                "See warnings above."
            )

        # 2. Clean ~* directories in site-packages
        await self._clean_tilde_dirs(ui_enabled)

        # 3. Pre-install pip groups (e.g. Triton, adjusted for detected torch)
        if addon.pre_pip_groups:
            # Re-create Triton group with detected torch version
            pre_groups: list[PipPackageGroup] = []
            for pg in addon.pre_pip_groups:
                if pg.name.startswith("triton-for-torch"):
                    pre_groups.append(
                        PipPackageGroup.triton_for_torch(versions.get("torch", "2.9"))
                    )
                else:
                    pre_groups.append(pg)
            await env_mgr.install_pip_groups(pre_groups, ui_enabled=ui_enabled)

        # 4. Clone git repos
        if addon.git_clones:
            # Remove existing dirs first (like batch scripts do with rmdir /s /q)
            for t in addon.git_clones:
                target_path = self.base_dir / t.dest_dir
                if target_path.exists():
                    AioUtils.remove_directory(target_path, ui_enabled=ui_enabled)
            await env_mgr.clone_all(
                addon.git_clones, cwd=self.base_dir, ui_enabled=ui_enabled
            )

        # 5. Resolve wheel URL from matrix
        wheel_url = self._resolve_wheel(addon.wheel_matrix, versions)

        # 6. Install pip groups (inject wheel URL into the first empty group)
        for group in addon.pip_groups:
            if not group.packages and wheel_url:
                group = PipPackageGroup(
                    name=group.name,
                    packages=[wheel_url],
                    extra_args=group.extra_args,
                    force_reinstall=group.force_reinstall,
                    no_deps=group.no_deps,
                )
            await env_mgr.install_pip(group, ui_enabled=ui_enabled)

        # 7. Install uv groups
        if addon.uv_groups:
            await env_mgr.install_uv_pip_groups(
                addon.uv_groups, ui_enabled=ui_enabled
            )

        # 8. Shell commands
        if addon.shell_commands:
            for cmd in addon.shell_commands:
                await env_mgr.shell_run(cmd, ui_enabled=ui_enabled)

        console.print(f"[bold green]=== {addon.name} Installation Complete ===[/]")

    # ================================================================
    # Update (mirrors Update ComfyUI and Nodes.bat)
    # ================================================================

    async def run_update(self, ui_enabled: bool = True) -> None:
        """Update ComfyUI and all custom nodes."""
        env_mgr = self._make_env_mgr()
        comfyui_dir = self.base_dir / "ComfyUI"

        console.print("[bold green]=== Updating ComfyUI ===[/]")

        # Checkout master
        await AioUtils.shell_cmd(
            ["git", "checkout", "master", "-q"],
            cwd=comfyui_dir,
            ui_enabled=ui_enabled,
        )

        # Install working av version
        await env_mgr.install_uv_pip(
            UvPackageGroup.av_package(), ui_enabled=ui_enabled
        )

        # Run update script
        update_dir = self.base_dir / "update"
        await AioUtils.shell_cmd(
            [str(env_mgr.python_exe), str(update_dir / "update.py"), str(comfyui_dir)],
            capture_output=True,
            ui_enabled=ui_enabled,
        )

        # Clean ~* directories
        await self._clean_tilde_dirs(ui_enabled)

        # Update all nodes via ComfyUI-Manager
        manager_cli = (
            comfyui_dir / "custom_nodes" / "ComfyUI-Manager" / "cm-cli.py"
        )
        if manager_cli.exists():
            console.print("[green]::: Updating [yellow]All Nodes[/]")
            await AioUtils.shell_cmd(
                [str(env_mgr.python_exe), "-I", str(manager_cli), "update", "all"],
                capture_output=True,
                ui_enabled=ui_enabled,
            )

        # Restore numpy
        await env_mgr.install_pip(
            PipPackageGroup.numpy_1_26_4(), ui_enabled=ui_enabled
        )

        console.print("[bold green]=== Update Complete ===[/]")

    # ================================================================
    # Torch version switch (mirrors Torch-Pack/*.bat)
    # ================================================================

    async def switch_torch(
        self,
        torch_group: PipPackageGroup,
        ui_enabled: bool = True,
    ) -> None:
        """Switch the installed Torch version."""
        env_mgr = self._make_env_mgr()

        console.print(f"[bold green]=== Switching to {torch_group.name} ===[/]")

        # Uninstall current torch
        await AioUtils.shell_cmd_py_pip(
            env_mgr.python_exe,
            ["torch", "torchvision", "torchaudio"],
            extra_args=["--yes"],
            ui_enabled=ui_enabled,
        )

        # Install new torch
        await env_mgr.install_pip(torch_group, ui_enabled=ui_enabled)

        console.print("[bold green]=== Torch Switch Complete ===[/]")
        console.print(
            "[bold yellow]!!! Make sure to reinstall Nunchaku, "
            "SageAttention and FlashAttention !!![/]"
        )

    # ================================================================
    # Helpers
    # ================================================================

    async def _clean_tilde_dirs(self, ui_enabled: bool = True) -> None:
        """Remove ~* directories from site-packages (cleanup leftovers)."""
        site_packages = (
            self.base_dir / "python_embeded" / "Lib" / "site-packages"
        )
        if not site_packages.exists():
            return

        for d in site_packages.iterdir():
            if d.is_dir() and d.name.startswith("~"):
                AioUtils.remove_directory(d, ui_enabled=ui_enabled)

    @staticmethod
    def _resolve_wheel(
        matrix: list[WheelMatrix],
        versions: dict[str, str],
    ) -> str | None:
        """Find matching wheel URL from version matrix."""
        py = versions.get("python", "")
        torch = versions.get("torch", "")
        cuda = versions.get("cuda", "")

        for entry in matrix:
            py_match = not entry.python_ver or entry.python_ver == py
            torch_match = not entry.torch_ver or entry.torch_ver == torch
            cuda_match = not entry.cuda_ver or entry.cuda_ver == cuda
            if py_match and torch_match and cuda_match:
                return entry.wheel_url

        return None
