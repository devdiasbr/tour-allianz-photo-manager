@echo off
setlocal
cd /d "%~dp0"

title Tour Allianz - Photo Manager

echo ============================================================
echo   Tour Allianz Parque - Photo Manager
echo ============================================================
echo.

if not exist "venv\Scripts\python.exe" (
  echo [ERRO] Ambiente virtual nao encontrado em .\venv
  echo.
  echo Crie o ambiente antes de rodar este script:
  echo    python -m venv venv
  echo    venv\Scripts\pip.exe install -r requirements.txt
  echo.
  pause
  exit /b 1
)

if not exist "venv\Scripts\uvicorn.exe" (
  echo [AVISO] Dependencias ainda nao instaladas. Instalando agora...
  echo.
  venv\Scripts\pip.exe install -r requirements.txt
  if errorlevel 1 (
    echo.
    echo [ERRO] Falha ao instalar dependencias.
    pause
    exit /b 1
  )
  echo.
)

set HOST=127.0.0.1
set PORT=8000

echo Iniciando servidor em http://%HOST%:%PORT% ...

start "Tour Allianz - Servidor" /min venv\Scripts\python.exe -m uvicorn server:app --host %HOST% --port %PORT%

powershell -NoProfile -Command "$u='http://%HOST%:%PORT%'; for($i=0;$i -lt 60;$i++){ try { [void](Invoke-WebRequest -UseBasicParsing -TimeoutSec 1 $u); exit 0 } catch { Start-Sleep -Milliseconds 500 } }; exit 1"

start "" "http://%HOST%:%PORT%"
exit /b 0
