@echo off
setlocal EnableDelayedExpansion
cd /d %~dp0

set PYTHON_CMD=
call :check_python python
if defined PYTHON_CMD goto :python_found
call :check_python py
if defined PYTHON_CMD goto :python_found
call :check_python python3
if defined PYTHON_CMD goto :python_found

echo.
echo [ERROR] A usable Windows Python installation was not found.
pause
exit /b 1

:check_python
%1 -c "import sys; assert sys.version_info >= (3,11); print(sys.executable)" >nul 2>nul
if %errorlevel%==0 set PYTHON_CMD=%1
exit /b 0

:python_found
if exist .venv (
    if not exist .venv\Scripts\python.exe rmdir /s /q .venv
)
if not exist .venv (
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 goto :fail
)

call .venv\Scripts\activate.bat
if errorlevel 1 goto :fail

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller
if errorlevel 1 goto :fail

python -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --hidden-import PySide6.QtPositioning ^
    --icon "assets\weather_notify.ico" ^
    --add-data "assets;assets" ^
    --name WeatherNotify ^
    main.py
if errorlevel 1 goto :fail

echo.
echo Build successful:
echo %CD%\dist\WeatherNotify.exe
explorer "%CD%\dist"
pause
exit /b 0

:fail
echo.
echo [ERROR] Build failed.
pause
exit /b 1
