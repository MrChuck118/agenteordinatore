@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

set APP_NAME=Agent Ordinatore
set PORTABLE_EXE=dist\%APP_NAME%\%APP_NAME%.exe

if exist "%PORTABLE_EXE%" (
    start "" "%PORTABLE_EXE%"
    exit /b 0
)

set PYTHONW_EXE=
for %%V in (313 312 311 310) do (
    if not defined PYTHONW_EXE (
        if exist "%LocalAppData%\Programs\Python\Python%%V\pythonw.exe" (
            set "PYTHONW_EXE=%LocalAppData%\Programs\Python\Python%%V\pythonw.exe"
        )
    )
)

if defined PYTHONW_EXE (
    start "" "%PYTHONW_EXE%" gui.py
) else (
    start "" pyw gui.py
)
