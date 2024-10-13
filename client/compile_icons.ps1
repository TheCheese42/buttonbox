# Must be run from an environment with pyside6 installed
pyside6-rcc client/buttonbox_client/icons/menu_icons.qrc | ForEach-Object { $_ -replace 'PySide6', 'PyQt6' } > client/buttonbox_client/icons/resource.py
