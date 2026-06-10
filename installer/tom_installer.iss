[Setup]
AppId={{B4E2C3A6-6D7F-4F3C-A5B6-6B72B11F2A24}
AppName=TOM Desktop
AppVersion=1.0.0
AppPublisher=TOM
DefaultDirName={autopf}\TOM Desktop
DefaultGroupName=TOM Desktop
OutputBaseFilename=TOM-Installer
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=no
DisableDirPage=no
SetupIconFile=..
esources	om_icon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "..\dist\tom_desktop_app.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\resources\*"; DestDir: "{app}\resources"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\TOM Desktop"; Filename: "{app}\tom_desktop_app.exe"; WorkingDir: "{app}"; IconFilename: "{app}\resources\tom_icon.ico"
Name: "{autodesktop}\TOM Desktop"; Filename: "{app}\tom_desktop_app.exe"; WorkingDir: "{app}"; IconFilename: "{app}\resources\tom_icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\tom_desktop_app.exe"; Description: "Launch TOM Desktop"; Flags: nowait postinstall skipifsilent
