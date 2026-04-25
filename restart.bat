@echo off
setlocal
cd /d "%~dp0"

title Tour Allianz - Reiniciar Servidor

echo ============================================================
echo   Tour Allianz Parque - Reiniciar Servidor
echo ============================================================
echo.

if not exist "stop.bat" (
  echo [ERRO] Arquivo stop.bat nao encontrado.
  pause
  exit /b 1
)

if not exist "start.bat" (
  echo [ERRO] Arquivo start.bat nao encontrado.
  pause
  exit /b 1
)

call ".\stop.bat"
if errorlevel 1 (
  echo.
  echo [ERRO] Falha ao encerrar o servidor. Reinicio cancelado.
  pause
  exit /b 1
)

echo.
echo Iniciando servidor novamente...
echo.

call ".\start.bat"
exit /b %errorlevel%
