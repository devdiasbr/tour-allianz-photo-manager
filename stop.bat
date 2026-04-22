@echo off
setlocal
cd /d "%~dp0"

title Tour Allianz - Parar Servidor

if not exist "server.pid" (
  echo Nenhum PID salvo encontrado. Servidor pode ja estar parado.
  timeout /t 2 /nobreak >nul
  exit /b 0
)

set "PID="
for /f "usebackq delims=" %%P in ("server.pid") do set "PID=%%P"

if "%PID%"=="" (
  echo Arquivo server.pid esta vazio ou invalido.
  del /q "server.pid" >nul 2>&1
  timeout /t 2 /nobreak >nul
  exit /b 0
)

tasklist /FI "PID eq %PID%" /NH 2>nul | find /I "%PID%" >nul
if errorlevel 1 (
  echo Processo %PID% nao esta mais em execucao.
  del /q "server.pid" >nul 2>&1
  timeout /t 2 /nobreak >nul
  exit /b 0
)

echo Encerrando servidor PID %PID%...
taskkill /F /PID %PID% >nul 2>&1

if errorlevel 1 (
  echo Falha ao encerrar o processo %PID%.
  timeout /t 2 /nobreak >nul
  exit /b 1
)

del /q "server.pid" >nul 2>&1
echo Servidor encerrado.
timeout /t 2 /nobreak >nul
exit /b 0
