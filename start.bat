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
set DNS_ALIAS=%HOST%
set "LOG_DIR=logs"

:: Variaveis de configuracao (descomente e ajuste conforme necessario)
:: "fast" (padrao) ou "accurate" (mais lento, melhor para rostos pequenos/escuros)
set FACE_SCAN_MODE=fast
:: threads por foto no scan (padrao: 1)
set FACE_SCAN_WORKERS=1
:: jobs de scan simultaneos (padrao: 2)
set SCAN_EXECUTOR_WORKERS=2
:: 1=rapido, 2=melhor deteccao de rostos pequenos
set FACE_UPSAMPLE=1
:: largura maxima para redimensionar antes do scan
set FACE_SCAN_MAX_WIDTH=800

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1

:: Encerra instancia anterior se houver (PID salvo por uma execucao previa).
if exist "server.pid" (
  echo Encerrando instancia anterior...
  for /f "usebackq delims=" %%P in ("server.pid") do (
    taskkill /F /PID %%P >nul 2>&1
  )
  del /q "server.pid" >nul 2>&1
  timeout /t 1 /nobreak >nul
)

:: Limpa output antes de iniciar
:: Cache mantido entre execucoes.
echo Limpando output anterior...
:: if exist "cache\detections.pkl" del /q "cache\detections.pkl" >nul 2>&1
:: Thumbs podem ficar em subpastas por evento dentro de cache\thumbnails.
:: if exist "cache\thumbnails" (
::   for /d %%D in ("cache\thumbnails\*") do rmdir /s /q "%%D" >nul 2>&1
::   for /f "usebackq delims=" %%F in (`dir /b /a-d /s "cache\thumbnails" 2^>nul`) do del /q "%%F" >nul 2>&1
:: )
if exist "output" (
  for /d %%D in ("output\*") do rmdir /s /q "%%D" >nul 2>&1
  for /f "usebackq delims=" %%F in (`dir /b /a-d "output" 2^>nul`) do del /q "output\%%F" >nul 2>&1
)
echo.

echo Iniciando servidor em http://%HOST%:%PORT% ...

:: Sobe python.exe sem janela. Captura stdout/stderr em arquivo pra ajudar diagnostico.
powershell -NoProfile -Command "$p = Start-Process -FilePath '.\venv\Scripts\python.exe' -ArgumentList '-m','uvicorn','server:app','--host','%HOST%','--port','%PORT%' -WindowStyle Hidden -RedirectStandardOutput '.\%LOG_DIR%\server-stdout.log' -RedirectStandardError '.\%LOG_DIR%\server-stderr.log' -PassThru; Set-Content -Path '.\server.pid' -Value $p.Id -Encoding ASCII"

:: Aguarda o servidor responder (poll ate 30s).
powershell -NoProfile -Command "for($i=0;$i -lt 60;$i++){ try { [void](Invoke-WebRequest -UseBasicParsing -TimeoutSec 1 'http://%HOST%:%PORT%'); exit 0 } catch { Start-Sleep -Milliseconds 500 } }; exit 1"

if errorlevel 1 (
  echo.
  echo [ERRO] Servidor nao respondeu em 30s.
  echo Veja %LOG_DIR%\server.log para detalhes do erro.
  pause
  exit /b 1
)

start "" "http://%HOST%:%PORT%"
exit /b 0
