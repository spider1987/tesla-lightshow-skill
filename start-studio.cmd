@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    set "STUDIO_PYTHON=%~dp0.venv\Scripts\python.exe"
    goto launch
)
if exist "C:\Program Files\Blender Foundation\Blender 5.1\5.1\python\bin\python.exe" (
    set "STUDIO_PYTHON=C:\Program Files\Blender Foundation\Blender 5.1\5.1\python\bin\python.exe"
    goto launch
)
where python >nul 2>nul
if errorlevel 1 (
    echo Python 3.11 oder neuer installieren. Siehe WEBSTUDIO.md.
    exit /b 1
)
set "STUDIO_PYTHON=python"
:launch
"%STUDIO_PYTHON%" run_studio.py %*
exit /b %errorlevel%
