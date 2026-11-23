@echo off
rem Compila wstb.dll (requiere Visual Studio Build Tools con C++ y Windows SDK).
setlocal
cd /d "%~dp0"
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
for /f "usebackq delims=" %%i in (`call "%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "VS=%%i"
if not defined VS (echo No se encontro Visual Studio Build Tools con C++.& exit /b 1)
call "%VS%\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1 || exit /b 1
set "OBJ=%TEMP%\wstb_build"
if not exist "%OBJ%" mkdir "%OBJ%"
cl /nologo /std:c++20 /EHsc /O2 /MT /LD /permissive- /DNOMINMAX /DUNICODE /D_UNICODE wstb.cpp styler.cpp /Fo"%OBJ%\\" /link /DEF:wstb.def /OUT:wstb.dll /IMPLIB:"%OBJ%\wstb.lib" /PDB:"%OBJ%\wstb.pdb"
set "RC=%errorlevel%"
rmdir /s /q "%OBJ%" 2>nul
del /q wstb.exp 2>nul
exit /b %RC%
