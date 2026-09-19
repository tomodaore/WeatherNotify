@echo off
setlocal

set "INSTALL_DIR=%LOCALAPPDATA%\Programs\WeatherNotify"
set "TARGET=%INSTALL_DIR%\WeatherNotify.exe"

taskkill /IM WeatherNotify.exe /F >nul 2>nul

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$desktop=[Environment]::GetFolderPath('Desktop');" ^
  "$start=Join-Path ([Environment]::GetFolderPath('StartMenu')) 'Programs';" ^
  "Remove-Item -LiteralPath (Join-Path $desktop 'Weather Notify.lnk') -Force -ErrorAction SilentlyContinue;" ^
  "Remove-Item -LiteralPath (Join-Path $start 'Weather Notify.lnk') -Force -ErrorAction SilentlyContinue;"

if exist "%INSTALL_DIR%" rmdir /s /q "%INSTALL_DIR%"

echo Weather Notify application and shortcuts were removed.
echo Your saved settings in %%USERPROFILE%%\.weather_notify were NOT deleted.
pause
