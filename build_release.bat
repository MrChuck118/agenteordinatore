@echo off
setlocal
cd /d "%~dp0"

set NO_PAUSE=1

call build_exe.bat
if errorlevel 1 exit /b 1

call build_installer.bat
if errorlevel 1 exit /b 1

exit /b 0
