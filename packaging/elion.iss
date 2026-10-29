; Dünne Einrichtung: nur ELION. Ollama ist nicht eingebettet.
[Setup]
AppId={{7C4E9A21-6B18-4F0D-9E33-1A2B3C4D5E6F}
AppName=ELION
AppVersion=0.9.0
AppVerName=ELION 0.9.0 Test
DefaultDirName={autopf}\ELION
DefaultGroupName=ELION
OutputDir=..\dist
OutputBaseFilename=ELION-Setup-0.9.0-test
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
UninstallDisplayName=ELION
WizardStyle=modern
InfoBeforeFile=liesmich.txt
DisableWelcomePage=no

[Languages]
Name: "de"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Verknüpfung auf dem Desktop"; GroupDescription: "Zusätzliche Symbole:"
Name: "ollama"; Description: "Offizielle Ollama-Downloadseite öffnen (separates Programm, nicht in ELION enthalten)"; GroupDescription: "Ollama:"; Flags: unchecked

[Files]
Source: "..\dist\ELION\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\ELION"; Filename: "{app}\ELION.exe"
Name: "{autodesktop}\ELION"; Filename: "{app}\ELION.exe"; Tasks: desktopicon

[Run]
Filename: "{cmd}"; Parameters: "/c start https://ollama.com/download"; Tasks: ollama; Flags: runhidden nowait postinstall skipifsilent
Filename: "{app}\ELION.exe"; Description: "ELION jetzt starten"; Flags: nowait postinstall skipifsilent
