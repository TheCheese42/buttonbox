# Buttonbox

the BOX.
schematics below (may be changed)

![image](https://github.com/user-attachments/assets/a2a05848-047d-4d3a-822e-e431287554a5)

Wokwi project: <https://wokwi.com/projects/410915727655762945>

## Microcontroller client

The Microcontroller client can be found at `/buttonbox/buttonbox.ino` and uploaded to an esp32 e.g. using Arduino IDE.
Everything that needs to be adapted is marked with a `# ADAPT` comment. It needs to run all the time, connected with the PC.

## PC client

The PC client is found it `/client` and is implemented as a PyQt6 application that runs in the background all the time (can be stopped from the GUI under `File -> Quit`).

### Build

First compile UI and icons by executing the `/client/compile-ui.sh` and `/client/compile-icons.sh` files. While those are Linux shell files, the client itself is cross-platform.

When bundling an executable, the following files and directories must be included:

- `/client/buttonbox_client/icons/resource.py`
- `/client/buttonbox_client/icons/cube-icon.png`
- `/client/buttonbox_client/ui/*_ui.py`
- `/client/buttonbox_client/__init__.py`
- `/client/buttonbox_client/config.py`
- `/client/buttonbox_client/gui.py`
- `/client/buttonbox_client/version.py`
- `PyQt6`, `pystray`, `pillow` and `pyserial` top level dependencies

The main file is `/client/buttonbox_client/__main__.py`.
