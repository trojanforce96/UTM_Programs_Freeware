@echo off
setlocal
set "ROOT=%~dp0..\.."
set "UTM=%~dp0.."
set "PYTHONPATH=%UTM%\bin;%ROOT%\bin"
title Build Student EXE

echo.
echo  Building UTM STUDENT edition exe
echo  Output: exe\UTM_Coordinate_Wizard_Student.exe
echo  (Malaysia.utm + sealed geoid embedded)
echo.

cd /d "%UTM%"

python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Install Python to build executables.
    pause
    exit /b 1
)

python "%UTM%\bin\tools\generate_branding.py"
if errorlevel 1 pause & exit /b 1
python "%UTM%\bin\tools\build_edition_exe.py" student
if errorlevel 1 (
    echo  [ERROR] Build failed.
    pause
    exit /b 1
)

echo  Opening exe folder???
start "" "%UTM%\exe"
pause

