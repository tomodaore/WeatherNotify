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
echo.
echo Windows may be finding only the Microsoft Store "App execution alias".
echo.
echo Please install Python 3.11 or later from:
echo https://www.python.org/downloads/windows/
echo.
echo During installation, enable:
echo   Add python.exe to PATH
echo.
echo If Python is already installed:
echo   Settings ^> Apps ^> Advanced app settings ^> App execution aliases
echo   Turn OFF python.exe and python3.exe aliases,
echo   then reopen this file.
echo.
pause
exit /b 1

:check_python
%1 -c "import sys; assert sys.version_info >= (3,11); print(sys.executable)" > "%TEMP%\weather_notify_python.txt" 2>nul
if %errorlevel%==0 (
    set PYTHON_CMD=%1
)
exit /b 0

:python_found
echo Using: %PYTHON_CMD%
%PYTHON_CMD% -c "import sys; print('Python', sys.version.split()[0]); print(sys.executable)"

if exist .venv (
    if not exist .venv\Scripts\python.exe (
        echo.
        echo Existing .venv is invalid. Recreating it...
        rmdir /s /q .venv
    )
)

if not exist .venv (
    echo.
    echo Creating virtual environment...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to create virtual environment.
        echo.
        echo Try running this command manually:
        echo   %PYTHON_CMD% -m venv .venv
        echo.
        pause
        exit /b 1
    )
)

call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)

echo.
echo Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo Starting Weather Notify...
python main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Application exited with an error.
    pause
)
exit /b 0
