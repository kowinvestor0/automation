; Inno Setup 6 script for the Automation Hub.
;
; Built by tools/build_setup.py, which passes the version and the paths in:
;   ISCC /DAppVersion=1.0.0 /DSourceDir=..\dist\AutomationHub installer\AutomationHub.iss
; The defaults below let a bare "ISCC AutomationHub.iss" work too.
;
; The user's complaint about the previous installer was that it never asked
; where to install. Everything about the pages below follows from that: the
; directory page is shown, it accepts any drive, and the installer runs without
; an admin prompt so nothing forces it onto C:.

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\dist\AutomationHub"
#endif
#ifndef OutDir
  #define OutDir "..\dist\setup"
#endif

#define AppName "Automation Hub"
#define AppExe "AutomationHub.exe"
#define AppPublisher "Automation Hub"

; Inno 6 does not bundle a Vietnamese translation - it is a third-party .isl
; from innosetup.com that has to be dropped into Languages\ by hand. Ship it
; when it is there, fall back to English when it is not, so the same script
; compiles on this PC and on the GitHub runner.
#if FileExists(AddBackslash(CompilerPath) + "Languages\Vietnamese.isl")
  #define HaveVietnamese
#endif

[Setup]
; Fixed forever. Change it and Windows treats the next release as a second
; program instead of an upgrade, and the user ends up with two of them.
AppId={{7B3C1E4A-9D52-4F86-A1C7-0E5B8A6D3F21}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
VersionInfoVersion={#AppVersion}

DefaultDirName={autopf}\AutomationHub
DefaultGroupName={#AppName}
AllowNoIcons=yes
; The whole point. Never set DisableDirPage=auto here: on an upgrade "auto"
; hides the page, and hiding it is the bug being fixed.
DisableDirPage=no
DisableProgramGroupPage=yes
DisableWelcomePage=no
; Any drive, any folder, including a second disk with room for the videos.
UsePreviousAppDir=yes

; Per-user by default, so no UAC prompt and no admin account needed. The user
; can still click through to an elevated install from the wizard, and then
; {autopf} resolves to Program Files instead of the local app data folder.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

OutputDir={#OutDir}
OutputBaseFilename=AutomationHub_Setup_{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; 64-bit only build. "x64" rather than "x64compatible" because the older name
; is accepted by every Inno 6 release, and the runner's version is not pinned.
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
MinVersion=10.0
UninstallDisplayName={#AppName} {#AppVersion}
UninstallDisplayIcon={app}\{#AppExe}
; ~200 MB of python runtime and bundled factories; keeps the disk-space check
; on the confirm page honest.
ExtraDiskSpaceRequired=0

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
#ifdef HaveVietnamese
Name: "vi"; MessagesFile: "compiler:Languages\Vietnamese.isl"
#endif

[CustomMessages]
en.CreateDesktopIcon=Create a desktop shortcut
en.CreateStartMenuIcon=Create a Start menu shortcut
en.LaunchApp=Open Automation Hub now
en.WorkspaceNote=Videos and settings are written to your user folder, never into the install folder, so this can go on any drive.
#ifdef HaveVietnamese
vi.CreateDesktopIcon=Tao bieu tuong tren man hinh
vi.CreateStartMenuIcon=Tao bieu tuong trong Start menu
vi.LaunchApp=Mo Automation Hub ngay
vi.WorkspaceNote=Video va cai dat duoc ghi vao thu muc nguoi dung, khong ghi vao thu muc cai dat, nen co the cai vao bat ky o dia nao.
#endif

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "startmenuicon"; Description: "{cm:CreateStartMenuIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; The one-folder PyInstaller build, verbatim. Nothing here is ever written to
; at run time - settings live in %APPDATA%\AutomationHub and the videos in the
; workspace the user picks inside the app - so this stays installable into
; Program Files without needing admin rights afterwards.
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: startmenuicon
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"; Tasks: startmenuicon
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchApp}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; PyInstaller drops .pyc files beside the bundled modules on first run; without
; this the uninstaller leaves an empty tree behind.
Type: filesandordirs; Name: "{app}\_internal\__pycache__"

[Code]
procedure CurPageChanged(CurPageID: Integer);
begin
  // Says on the directory page itself that another drive is fine, because the
  // user has been burned by an installer that quietly chose C: for them.
  if CurPageID = wpSelectDir then
    WizardForm.DirEdit.Hint := ExpandConstant('{cm:WorkspaceNote}');
end;
