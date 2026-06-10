TOM Installer

This folder contains an Inno Setup script that can package the built TOM exe into a normal Windows installer.

Prerequisites:
- `dist\tom_desktop_app.exe` built with PyInstaller
- `resources\tom_icon.ico`
- Inno Setup installed on the machine that will build the installer

Build command when Inno Setup is installed:

  iscc installer\tom_installer.iss

Output:
- `TOM-Installer.exe`
