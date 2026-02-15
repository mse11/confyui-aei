User Review Required
IMPORTANT

The batch scripts contain Windows-specific operations that don't translate cleanly to Python (e.g., creating .lnk desktop shortcuts, PowerShell folder-browse dialogs, registry edits for long-path support, WinForms license dialogs). These are excluded from the initial port. Only the core install/setup pipeline is ported.

IMPORTANT

The Easy-Models-Linker.bat writes a extra_model_paths.yaml file interactively. It is excluded from this port since it requires a GUI folder browser that is beyond the scope.

WARNING

The batch scripts are version-locked (fixed wheel URLs per Python/Torch/CUDA combos). The configuration classes encode these same version matrices. If upstream releases new wheels you need to update the config definitions.
