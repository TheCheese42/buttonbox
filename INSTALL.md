# Building Buttonbox

## Windows

A Windows Installer will be available for Download once the initial Release is published.

A portable Executable will also be available for Download.

## Linux

A portable Linux Executable will be available for Download once the initial Release is published.

## Running from Source

The Client is cross-platform, so it should work on any system if running from source or compiled manually.

For the PyQt6 Application to run, some Qt Resources must be compiled.

First compile UI and icons by executing the `/client/compile-ui.sh` and `/client/compile-icons.sh` (UNIX/Bash) or `/client/compile_ui.ps1` and `/client/compile_icons.ps1` (Windows/PowerShell) files.
Note that for the `compile-icons.sh` and `compile_icons.ps1` files, PySide6 must be installed. For everything else, PyQt6 is used.

### Bundling an Executable

When bundling an Executable, the following files and directories must be included:

- `/client/buttonbox_client/icons/resource.py`
- `/client/buttonbox_client/icons/cube-icon.png`
- `/client/buttonbox_client/ui/*_ui.py`
- `/client/buttonbox_client/__init__.py`
- `/client/buttonbox_client/config.py`
- `/client/buttonbox_client/gui.py`
- `/client/buttonbox_client/model.py`
- `/client/buttonbox_client/version.py`
- `/client/buttonbox_client/empty_profile.json`
- `/client/buttonbox_client/licenses/LICENSES.html` (See below)
- `PyQt6`, `pystray`, `pillow`, `pyserial` and `pynput` top level dependencies

The main file is `/client/buttonbox_client/__main__.py`.

For the Open Source Licenses Dialog to function properly, the appropriate License file from `/client/buttonbox_client/licenses/` must be copied to `/client/buttonbox_client/licenses/LICENSES.html`.

A nuitka build script will be included in the future.
