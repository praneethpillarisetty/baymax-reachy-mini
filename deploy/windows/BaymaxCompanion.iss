[Setup]
AppName=Baymax Companion
AppVersion=0.3.0
DefaultDirName={localappdata}\Programs\BaymaxCompanion
DefaultGroupName=Baymax Companion
UninstallDisplayName=Baymax Companion
OutputBaseFilename=BaymaxCompanion-Setup
OutputDir=..\..\dist

[Files]
Source: "..\..\dist\BaymaxCompanion.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\config\*"; DestDir: "{localappdata}\BaymaxCompanion\config"; Flags: recursesubdirs onlyifdoesntexist

[Icons]
Name: "{group}\Baymax Companion"; Filename: "{app}\BaymaxCompanion.exe"
