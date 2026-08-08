@echo off
setlocal
set "ROOT=%~dp0..\.."
set "UTM=%~dp0.."
set "PYTHONPATH=%UTM%\bin;%ROOT%\bin"
title Build Lecturer Package

echo.
echo  ====================================================
echo    1. Replace logo/icon in bin\branding\lecturer\
echo       and bin\branding\student\  (optional)
echo    2. Build branded lecturer exe + student template
echo    3. Package for your lecturer (exe + Malaysia.xml)
echo  ====================================================
echo.

cd /d "%UTM%"
python "%UTM%\bin\tools\build_lecturer_package.py"
if errorlevel 1 pause & exit /b 1
echo  Opening lecturer package folder???
start "" "%UTM%\dist\UTM_Coordinate_Wizard_Lecturer"
pause

