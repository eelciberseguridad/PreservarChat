@echo off
setlocal
cd /d "%~dp0"
for %%F in ("dist\*.exe") do (
  if exist "%%~fF" (
    echo ============================================================
    echo %%~nxF
    certutil -hashfile "%%~fF" SHA256
    certutil -hashfile "%%~fF" SHA512
    echo.
  )
)
pause
