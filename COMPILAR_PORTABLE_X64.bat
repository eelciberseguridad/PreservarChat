@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title PreservarChat 2.5 FINAL x64

echo ============================================================
echo PreservarChat 2.5 FINAL - EXE PORTABLE x64
echo ============================================================
echo.

where py >nul 2>nul
if errorlevel 1 (
  echo ERROR: no se encontro el lanzador de Python "py".
  pause
  exit /b 1
)

for /f "delims=" %%A in ('py -3-64 -c "import struct;print(struct.calcsize('P')*8)" 2^>nul') do set "PYBITS=%%A"
if not "%PYBITS%"=="64" (
  echo ERROR: no se encontro Python de 64 bits mediante: py -3-64
  echo Instala Python de 64 bits y vuelve a intentar.
  pause
  exit /b 1
)

echo [1/4] Python:
py -3-64 --version
echo.

echo [2/4] Actualizando pip...
py -3-64 -m pip install --upgrade pip
if errorlevel 1 goto :error

echo [3/4] Instalando dependencias...
py -3-64 -m pip install -r "requirements-build-x64.txt"
if errorlevel 1 goto :error

echo [4/4] Compilando...
py -3-64 -m PyInstaller --noconfirm --clean --onefile --windowed --name "PreservarChat_SOLO_x64" --collect-all cv2 --version-file "version_info.txt" "PreservarChat.py"
if errorlevel 1 goto :error

if not exist "dist\PreservarChat_SOLO_x64.exe" goto :error

echo.
echo EXE generado:
echo %CD%\dist\PreservarChat_SOLO_x64.exe
echo.
echo SHA-256:
certutil -hashfile "dist\PreservarChat_SOLO_x64.exe" SHA256
echo.
pause
exit /b 0

:error
echo.
echo ERROR: no se pudo completar la compilacion.
echo Revisa la salida anterior. En x86 algunas dependencias pueden no disponer de wheel compatible.
pause
exit /b 1
