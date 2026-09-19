; Weather Notify distributable installer
; Built after PyInstaller creates ..\dist\WeatherNotify.exe

#define MyAppName "Weather Notify"
#define MyAppVersion "0.1.21"
#define MyAppExeName "WeatherNotify.exe"
#define MyAppId "{{7E58552B-7EA1-4DE5-B227-9B0D718C1F84}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher=Weather Notify
DefaultDirName={localappdata}\Programs\WeatherNotify
DefaultGroupName=Weather Notify
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist_setup
OutputBaseFilename=WeatherNotify_Setup_v{#MyAppVersion}
SetupIconFile=..\assets\weather_notify.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
UsePreviousAppDir=yes
VersionInfoVersion=0.1.21.0
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
VersionInfoDescription=Weather notification desktop application

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "デスクトップに Weather Notify のアイコンを作成"; GroupDescription: "追加アイコン:"

[Files]
Source: "..\dist\WeatherNotify.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\PRIVACY.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Weather Notify"; Filename: "{app}\WeatherNotify.exe"; WorkingDir: "{app}"
Name: "{userdesktop}\Weather Notify"; Filename: "{app}\WeatherNotify.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\WeatherNotify.exe"; Description: "Weather Notify を起動"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
