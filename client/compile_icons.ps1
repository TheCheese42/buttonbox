# Must be run from an environment with pyside6 installed
pyside6-rcc client/buttonbox_client/icons/menu_icons.qrc | ForEach-Object { $_ -replace 'PySide6', 'PyQt6' } > client/buttonbox_client/icons/resource.py
# Re-encode as utf-8 as pyside6-rcc tends to encode it as Macintosh (CR)
Get-Content client/buttonbox_client/icons/resource.py | Out-File -Encoding utf8 -Filepath client/buttonbox_client/icons/resource.py
