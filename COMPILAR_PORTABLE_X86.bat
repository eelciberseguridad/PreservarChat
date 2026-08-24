@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title PreservarChat 2.5 FINAL x32

echo ============================================================
echo PreservarChat 2.5 FINAL - EXE PORTABLE x32
echo ============================================================
echo.

where py >nul 2>nul
if errorlevel 1 (
  echo ERROR: no se encontro el lanzador de Python "py".
  pause
  exit /b 1
)

for /f "delims=" %%A in ('py -3-32 -c "import struct;print(struct.calcsize('P')*8)" 2^>nul') do set "PYBITS=%%A"
if not "%PYBITS%"=="32" (
  echo ERROR: no se encontro Python de 32 bits mediante: py -3-32
  echo Instala Python de 32 bits y vuelve a intentar.
  pause
  exit /b 1
)

echo [1/4] Python:
py -3-32 --version
echo.

echo [2/4] Actualizando pip...
py -3-32 -m pip install --upgrade pip
if errorlevel 1 goto :error

echo [3/4] Instalando dependencias...
py -3-32 -m pip install -r "requirements-build-x86.txt"
if errorlevel 1 goto :error

echo [4/4] Compilando...
py -3-32 -m PyInstaller --noconfirm --clean --onefile --windowed --name "PreservarChat_SOLO_x86" --version-file "version_info.txt" "PreservarChat.py"
if errorlevel 1 goto :error

if not exist "dist\PreservarChat_SOLO_x86.exe" goto :error

echo.
echo EXE generado:
echo %CD%\dist\PreservarChat_SOLO_x86.exe
echo.
echo SHA-256:
certutil -hashfile "dist\PreservarChat_SOLO_x86.exe" SHA256
echo.
pause
exit /b 0

:error
echo.
echo ERROR: no se pudo completar la compilacion.
echo Revisa la salida anterior. En x86 algunas dependencias pueden no disponer de wheel compatible.
pause
exit /b 1
