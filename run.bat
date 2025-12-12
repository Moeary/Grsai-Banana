@echo off
setlocal

REM Try to find Anaconda installation
set "ANACONDA_PATH=D:\Programs\Anaconda"

if not exist "%ANACONDA_PATH%\Scripts\activate.bat" (
    echo Anaconda not found at %ANACONDA_PATH%
    echo Please edit this script to set the correct ANACONDA_PATH
    pause
    exit /b 1
)

echo Activating Anaconda environment...
call "%ANACONDA_PATH%\Scripts\activate.bat" base

echo Starting Banana Image Generator...
python main.py

if %ERRORLEVEL% NEQ 0 (
    echo Application exited with error code %ERRORLEVEL%
    pause
)
