# Buttonbox

The BOX.
Schematics below (may be changed).

![image](https://github.com/user-attachments/assets/a2a05848-047d-4d3a-822e-e431287554a5)

Wokwi project: <https://wokwi.com/projects/410915727655762945> (illustrational).

## Microcontroller client

The Microcontroller client can be found at `/buttonbox/buttonbox.ino` and uploaded to an esp32 e.g. using Arduino IDE.
Everything that needs to be adapted is marked with an `// ADAPT` comment. It needs to run all the time, connected to the PC.

## PC client

The PC client is found at `/client` and is implemented as a PyQt6 application that runs in the background all the time (can be stopped from the GUI under `File -> Quit`). It lives in the system tray/notification area.

![image](/screenshots/client_main.png)

### Build

First compile UI and icons by executing the `/client/compile-ui.sh` and `/client/compile-icons.sh` (UNIX/Bash) or `/client/compile_ui.ps1` and `/client/compile_icons.ps1` (Windows/PowerShell) files. The client itself is cross-platform. Note that for the `compile-icons.sh` and `compile_icons.ps1` files, PySide6 must be installed. For everything else, PyQt6 is used.

When bundling an executable, the following files and directories must be included:

- `/client/buttonbox_client/icons/resource.py`
- `/client/buttonbox_client/icons/cube-icon.png`
- `/client/buttonbox_client/ui/*_ui.py`
- `/client/buttonbox_client/__init__.py`
- `/client/buttonbox_client/config.py`
- `/client/buttonbox_client/gui.py`
- `/client/buttonbox_client/model.py`
- `/client/buttonbox_client/version.py`
- `/client/buttonbox_client/empty_profile.json`
- `PyQt6`, `pystray`, `pillow`, `pyserial` and `pynput` top level dependencies

The main file is `/client/buttonbox_client/__main__.py`.

A nuitka build script will be included in the future.
