"""CLI entry-point for confyui-aei.

Provides commands: install, addon, update, torch, check-versions.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import click

from .config import (
    AddonConfig,
    InstallerConfig,
    PipPackageGroup,
)
from .env_manager import PythonEnvManager
from .installer import ComfyUIInstaller


def _run(coro):
    """Run an async coroutine from sync click context."""
    asyncio.run(coro)


@click.group()
@click.version_option()
def cli():
    """ConfUI Advanced Easy Installer — Python port of ComfyUI-Easy-Install."""


# ======================================================================
# install
# ======================================================================


@cli.command()
@click.option(
    "--base-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path(".") / "ComfyUI-Easy-Install",
    show_default=True,
    help="Base directory for the installation.",
)
def install(base_dir: Path):
    """Run the full ComfyUI Easy Install (equivalent to ComfyUI-Easy-Install.bat)."""
    base_dir = base_dir.resolve()
    if base_dir.exists():
        click.confirm(
            f"Directory '{base_dir}' already exists. Continue?", abort=True
        )
    base_dir.mkdir(parents=True, exist_ok=True)

    config = InstallerConfig.comfyui_easy_install()
    orchestrator = ComfyUIInstaller(config, base_dir)
    _run(orchestrator.run_full_install())


# ======================================================================
# addon
# ======================================================================

ADDON_FACTORIES = {
    "flash-attention": AddonConfig.flash_attention,
    "sage-attention": AddonConfig.sage_attention,
    "sage-attention3": AddonConfig.sage_attention3,
    "nunchaku": AddonConfig.nunchaku,
    "insightface": AddonConfig.insightface,
    "trellis2": AddonConfig.trellis2,
}


@cli.command()
@click.argument("name", type=click.Choice(list(ADDON_FACTORIES.keys())))
@click.option(
    "--base-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path("."),
    show_default=True,
    help="Base directory of an existing ComfyUI-Easy-Install.",
)
def addon(name: str, base_dir: Path):
    """Install a ComfyUI add-on (FlashAttention, SageAttention, etc.)."""
    base_dir = base_dir.resolve()
    factory = ADDON_FACTORIES[name]
    addon_cfg = factory()

    config = InstallerConfig.comfyui_easy_install()
    orchestrator = ComfyUIInstaller(config, base_dir)
    _run(orchestrator.run_addon(addon_cfg))


# ======================================================================
# update
# ======================================================================


@cli.command()
@click.option(
    "--base-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path("."),
    show_default=True,
    help="Base directory of an existing ComfyUI-Easy-Install.",
)
def update(base_dir: Path):
    """Update ComfyUI and all custom nodes."""
    base_dir = base_dir.resolve()

    config = InstallerConfig.comfyui_easy_install()
    orchestrator = ComfyUIInstaller(config, base_dir)
    _run(orchestrator.run_update())


# ======================================================================
# torch
# ======================================================================

TORCH_PRESETS = {
    "2.9.1+cu130": PipPackageGroup.torch_291_cu130,
    "2.8.0+cu128": PipPackageGroup.torch_280_cu128,
    "2.7.1+cu128": PipPackageGroup.torch_271_cu128,
}


@cli.command(name="torch")
@click.argument("version", type=click.Choice(list(TORCH_PRESETS.keys())))
@click.option(
    "--base-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path("."),
    show_default=True,
    help="Base directory of an existing ComfyUI-Easy-Install.",
)
def switch_torch(version: str, base_dir: Path):
    """Switch Torch version (e.g. 2.9.1+cu130, 2.8.0+cu128, 2.7.1+cu128)."""
    base_dir = base_dir.resolve()
    torch_group = TORCH_PRESETS[version]()

    config = InstallerConfig.comfyui_easy_install()
    orchestrator = ComfyUIInstaller(config, base_dir)
    _run(orchestrator.switch_torch(torch_group))


# ======================================================================
# check-versions
# ======================================================================


@cli.command(name="check-versions")
@click.option(
    "--base-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path("."),
    show_default=True,
    help="Base directory of an existing ComfyUI-Easy-Install.",
)
def check_versions(base_dir: Path):
    """Show Python, Torch, and CUDA versions of the embedded environment."""
    base_dir = base_dir.resolve()
    python_exe = base_dir / "python_embeded" / "python.exe"

    if not python_exe.exists():
        click.echo(f"Error: {python_exe} not found.", err=True)
        raise SystemExit(1)

    from .config import PythonEmbedConfig
    env_mgr = PythonEnvManager(PythonEmbedConfig.python_3_12_10(), base_dir)
    _run(env_mgr.get_versions(ui_enabled=True))
