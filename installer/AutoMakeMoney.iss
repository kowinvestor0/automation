; Inno Setup 6 script for Auto Make Money Pro

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\dist\AutoMakeMoney"
#endif
#ifndef OutDir
  #define OutDir "..\dist\setup"
#endif

#define AppName "Auto Make Money Pro"
#define AppExe "AutoMakeMoney.exe"
#define AppPublisher "Auto Make Money"

[Setup]
AppId={{9D5E3F6C-1F74-5BA8-C3E9-2A8B0C8F5B43}}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
VersionInfoVersion={#AppVersion}

DefaultDirName=D:\AutoMakeMoney
DefaultGroupName={#AppName}
AllowNoIcons=yes
DisableDirPage=no
DisableProgramGroupPage=yes
DisableWelcomePage=no
UsePreviousAppDir=no

PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

OutputDir={#OutDir}
OutputBaseFilename=AutoMakeMoney_Setup_{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=force
CloseApplicationsFilter=*.exe
RestartApplications=no
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
MinVersion=10.0
UninstallDisplayName={#AppName} {#AppVersion}
UninstallDisplayIcon={app}\{#AppExe}
SetupIconFile=..\assets\app.ico

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
en.CreateDesktopIcon=Create desktop shortcut (Tao bieu tuong Desktop)
en.CreateStartMenuIcon=Create Start menu shortcut (Tao bieu tuong Start Menu)
en.LaunchApp=Launch Auto Make Money Pro now (Mo ung dung ngay)

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "startmenuicon"; Description: "{cm:CreateStartMenuIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: startmenuicon
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"; Tasks: startmenuicon
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchApp}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\_internal\__pycache__"
