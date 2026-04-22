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

:: Variaveis de configuracao (descomente e ajuste conforme necessario)
:: "fast" (padrao) ou "accurate" (mais lento, melhor para rostos pequenos/escuros)
set FACE_SCAN_MODE=accurate
:: threads por foto no scan (padrao: 1)
set FACE_SCAN_WORKERS=1
:: jobs de scan simultaneos (padrao: 2)
set SCAN_EXECUTOR_WORKERS=4
:: 1=rapido, 2=melhor deteccao de rostos pequenos
set FACE_UPSAMPLE=1
:: largura maxima para redimensionar antes do scan
set FACE_SCAN_MAX_WIDTH=800

:: Encerra instancia anterior se houver (PID salvo por uma execucao previa).
if exist "server.pid" (
  echo Encerrando instancia anterior...
  for /f "usebackq delims=" %%P in ("server.pid") do (
    taskkill /F /PID %%P >nul 2>&1
  )
  del /q "server.pid" >nul 2>&1
  timeout /t 1 /nobreak >nul
)

:: Limpa cache e output antes de iniciar
echo Limpando cache e output anteriores...
if exist "cache\detections.pkl" del /q "cache\detections.pkl" >nul 2>&1
if exist "cache\thumbnails" (
  for /f "usebackq delims=" %%F in (`dir /b /a-d "cache\thumbnails" 2^>nul`) do del /q "cache\thumbnails\%%F" >nul 2>&1
)
if exist "output" (
  for /d %%D in ("output\*") do rmdir /s /q "%%D" >nul 2>&1
  for /f "usebackq delims=" %%F in (`dir /b /a-d "output" 2^>nul`) do del /q "output\%%F" >nul 2>&1
)
echo.

echo Iniciando servidor em http://%HOST%:%PORT% ...

:: Sobe python.exe sem janela. Captura stdout/stderr em arquivo pra ajudar diagnostico.
powershell -NoProfile -Command "$p = Start-Process -FilePath '.\venv\Scripts\python.exe' -ArgumentList '-m','uvicorn','server:app','--host','%HOST%','--port','%PORT%' -WindowStyle Hidden -RedirectStandardOutput '.\server-stdout.log' -RedirectStandardError '.\server-stderr.log' -PassThru; Set-Content -Path '.\server.pid' -Value $p.Id -Encoding ASCII"

:: Aguarda o servidor responder (poll ate 30s).
powershell -NoProfile -Command "for($i=0;$i -lt 60;$i++){ try { [void](Invoke-WebRequest -UseBasicParsing -TimeoutSec 1 'http://%HOST%:%PORT%'); exit 0 } catch { Start-Sleep -Milliseconds 500 } }; exit 1"

if errorlevel 1 (
  echo.
  echo [ERRO] Servidor nao respondeu em 30s.
  echo Veja server.log para detalhes do erro.
  pause
  exit /b 1
)

start "" "http://%HOST%:%PORT%"
exit /b 0
