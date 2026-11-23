@echo off
rem Compila WinStyler.exe (portable, con icono). Al terminar solo queda WinStyler.exe en esta carpeta.
setlocal
cd /d "%~dp0"
if not exist "native\wstb.dll" (
  call "native\compilar_dll.bat" || (echo No se pudo compilar native\wstb.dll & exit /b 1)
)
set "PYI=pyinstaller"
where pyinstaller >nul 2>&1 || set "PYI=python -m PyInstaller"
if not exist "assets\logo.png" python "assets\crear_icono.py"
set "WORK=%TEMP%\winstyler_build_%RANDOM%"
%PYI% --noconfirm --clean --onefile --noconsole --log-level WARN --name WinStyler ^
  --icon "%~dp0assets\winstyler.ico" ^
  --add-data "%~dp0assets\winstyler.ico;assets" ^
  --add-data "%~dp0assets\logo.png;assets" ^
  --add-data "%~dp0mods;mods" ^
  --add-data "%~dp0themes;themes" ^
  --add-binary "%~dp0native\wstb.dll;native" ^
  --distpath "%~dp0." --workpath "%WORK%" --specpath "%WORK%" ^
  "%~dp0WinStyler.py"
set "RC=%errorlevel%"
rmdir /s /q "%WORK%" 2>nul
rmdir /s /q "__pycache__" 2>nul
if "%RC%"=="0" (echo Listo: %~dp0WinStyler.exe) else (echo Error al compilar.)
exit /b %RC%
