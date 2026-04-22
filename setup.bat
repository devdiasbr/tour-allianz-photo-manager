@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

title Tour Allianz - Setup

echo ============================================================
echo   Tour Allianz Parque - Setup de Ambiente
echo ============================================================
echo.
echo Este script ira:
echo   1. Instalar Python 3.12 (se necessario, via winget)
echo   2. Criar o ambiente virtual (venv)
echo   3. Instalar o dlib pre-compilado (wheel)
echo   4. Instalar as demais dependencias
echo.
echo Requer conexao com internet. Pode demorar alguns minutos.
echo.
pause

REM ----------------------------------------------------------------
REM  Compatibilidade minima
REM ----------------------------------------------------------------
if /I not "%PROCESSOR_ARCHITECTURE%"=="AMD64" (
  echo [ERRO] Este instalador suporta apenas Windows x64.
  echo        Arquitetura detectada: %PROCESSOR_ARCHITECTURE%
  pause
  exit /b 1
)

if exist "server.pid" if exist "stop.bat" (
  echo Servidor detectado. Encerrando antes do setup...
  call stop.bat
)

REM ----------------------------------------------------------------
REM  1. Python 3.12
REM ----------------------------------------------------------------
echo.
echo [1/4] Verificando Python 3.12...

set "PYEXE="
call :find_python312

if not defined PYEXE (
  where winget >nul 2>&1
  if errorlevel 1 (
    echo [ERRO] Python 3.12 nao encontrado e winget nao esta disponivel.
    echo        Atualize o Windows ou instale o "App Installer" da Microsoft Store.
    echo        Alternativamente, instale o Python 3.12 manualmente e rode o setup novamente.
    pause
    exit /b 1
  )

  echo Python 3.12 nao encontrado. Instalando via winget...
  winget install --id Python.Python.3.12 -e --source winget --accept-source-agreements --accept-package-agreements
  if errorlevel 1 (
    echo [ERRO] winget falhou ao instalar Python 3.12.
    echo        Instale manualmente em https://www.python.org/downloads/ e rode novamente.
    pause
    exit /b 1
  )

  set "PATH=%LocalAppData%\Programs\Python\Launcher;%LocalAppData%\Programs\Python\Python312;%PATH%"
  call :find_python312

  if not defined PYEXE (
    echo Python 3.12 foi instalado, mas nao ficou disponivel nesta sessao.
    echo Feche esta janela e rode setup.bat novamente.
    pause
    exit /b 0
  )
)

REM ----------------------------------------------------------------
REM  2. venv
REM ----------------------------------------------------------------
echo.
echo [2/4] Criando ambiente virtual em .\venv...

set "VENV_OK="
if exist "venv\Scripts\python.exe" (
  set "VENV_VERSION="
  for /f "usebackq delims=" %%V in (`venv\Scripts\python.exe -c "import sys; print('.'.join(map(str, sys.version_info[:2])))" 2^>nul`) do set "VENV_VERSION=%%V"
  if "!VENV_VERSION!"=="3.12" (
    set "VENV_OK=1"
    echo venv ja existe com Python 3.12, reutilizando.
  ) else (
    echo venv existente usa Python !VENV_VERSION!, recriando com Python 3.12...
    rmdir /s /q "venv"
    if exist "venv\Scripts\python.exe" (
      echo [ERRO] Nao foi possivel recriar a venv porque ela esta em uso.
      echo        Feche a aplicacao, rode stop.bat e execute o setup novamente.
      pause
      exit /b 1
    )
  )
)

if not defined VENV_OK (
  "%PYEXE%" -m venv venv
  if errorlevel 1 (
    echo [ERRO] Falha ao criar venv.
    pause
    exit /b 1
  )
  echo venv criada.
)

venv\Scripts\python.exe -m pip --version >nul 2>&1
if errorlevel 1 (
  echo pip ausente na venv. Reinstalando com ensurepip...
  venv\Scripts\python.exe -m ensurepip --upgrade
  if errorlevel 1 (
    echo [ERRO] Falha ao reinstalar o pip na venv.
    pause
    exit /b 1
  )
)

echo Atualizando pip, wheel e setuptools compativel...
venv\Scripts\python.exe -m pip install --upgrade pip wheel "setuptools<81"
if errorlevel 1 (
  echo [ERRO] Falha ao atualizar pip.
  pause
  exit /b 1
)

REM ----------------------------------------------------------------
REM  3. dlib (wheel pre-compilado)
REM ----------------------------------------------------------------
echo.
echo [3/4] Instalando dlib pre-compilado...

venv\Scripts\python.exe -c "import dlib" >nul 2>&1
if not errorlevel 1 (
  echo dlib ja instalado, pulando.
  goto :deps
)

set DLIB_URL=https://raw.githubusercontent.com/ZeroReiNull/dlib-python/main/dlib-19.24.2-cp312-cp312-win_amd64.whl
set DLIB_FILE=%TEMP%\dlib-19.24.2-cp312-cp312-win_amd64.whl

if not exist "%DLIB_FILE%" (
  echo Baixando wheel do dlib...
  powershell -NoProfile -Command "Invoke-WebRequest -Uri '%DLIB_URL%' -OutFile '%DLIB_FILE%' -UseBasicParsing"
  if errorlevel 1 (
    echo [ERRO] Falha ao baixar o wheel do dlib.
    echo        URL: %DLIB_URL%
    echo        Verifique sua conexao ou coloque o arquivo manualmente em:
    echo        %DLIB_FILE%
    pause
    exit /b 1
  )
) else (
  echo Wheel do dlib encontrado, pulando download.
)

REM Valida que o arquivo e um zip/wheel real (comeca com PK)
powershell -NoProfile -Command "$b=(Get-Content -Encoding Byte -ReadCount 2 -TotalCount 2 '%DLIB_FILE%')[0]; if ($b[0] -ne 80 -or $b[1] -ne 75) { Write-Error 'Arquivo invalido'; exit 1 }"
if errorlevel 1 (
  echo [ERRO] O arquivo nao e um wheel valido ^(possivel erro de rede ou bloqueio corporativo^).
  echo        Tente novamente ou baixe manualmente:
  echo        %DLIB_URL%
  echo        e coloque em: %DLIB_FILE%
  del "%DLIB_FILE%" >nul 2>&1
  pause
  exit /b 1
)

venv\Scripts\python.exe -m pip install "%DLIB_FILE%"
if errorlevel 1 (
  echo [ERRO] Falha ao instalar o dlib.
  pause
  exit /b 1
)
del "%DLIB_FILE%" >nul 2>&1

REM ----------------------------------------------------------------
REM  4. demais dependencias
REM ----------------------------------------------------------------
:deps
echo.
echo [4/4] Instalando demais dependencias...

if not exist "requirements.txt" (
  echo [ERRO] Arquivo requirements.txt nao encontrado.
  pause
  exit /b 1
)

echo Instalando pacotes do requirements.txt...
venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
  echo [ERRO] Falha ao instalar dependencias do requirements.txt.
  pause
  exit /b 1
)

REM Verificacao final
echo.
echo Verificando instalacao...
venv\Scripts\python.exe -c "import fastapi, uvicorn, cv2, PIL, numpy, win32api, pkg_resources; from app.services import face_service; print('OK - dependencias instaladas')"
if errorlevel 1 (
  echo [AVISO] Alguns modulos falharam ao carregar. Veja a mensagem acima.
  pause
  exit /b 1
)

venv\Scripts\python.exe -c "import numpy as np; from app.services import face_service; img=np.zeros((32,32,3), dtype=np.uint8); face_service.get_face_locations(img); print('OK - detector operacional')"
if errorlevel 1 (
  echo [ERRO] O detector facial nao conseguiu processar uma imagem RGB simples.
  echo        Verifique a compatibilidade entre numpy e dlib neste ambiente.
  pause
  exit /b 1
)

venv\Scripts\python.exe -c "import os, sys; sys.exit(10 if any(ord(c) > 127 for c in os.getcwd()) else 0)"
if errorlevel 10 (
  echo.
  echo [AVISO] A pasta atual contem acentos ou caracteres especiais.
  echo         O dlib/face_recognition pode falhar nesses caminhos no Windows.
  echo         Para a maquina de destino, prefira instalar em uma pasta simples como C:\ESP.
)

echo %CD% | find /I "OneDrive" >nul
if not errorlevel 1 (
  echo.
  echo [AVISO] A pasta atual esta dentro do OneDrive.
  echo         Para evitar travas e problemas de caminho, prefira uma pasta local como C:\ESP.
)

echo.
echo ============================================================
echo   Setup concluido com sucesso!
echo ============================================================
echo.
echo Observacao: se a impressao abrir o visualizador em vez de
echo imprimir, rode docs\fix-print-apply.reg como administrador
echo (botao direito -^> Mesclar).
echo.
echo Iniciando a aplicacao...
call start.bat
set "START_EXIT=%ERRORLEVEL%"
endlocal & set "START_EXIT=%START_EXIT%"

if not "%START_EXIT%"=="0" (
  echo.
  echo [ERRO] O setup terminou, mas o start.bat falhou.
  pause
  exit /b %START_EXIT%
)

exit /b 0

:find_python312
set "PYEXE="
for /f "usebackq delims=" %%P in (`py -3.12 -c "import sys; print(sys.executable)" 2^>nul`) do set "PYEXE=%%P"
if defined PYEXE goto :show_python

if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
  set "PYEXE=%LocalAppData%\Programs\Python\Python312\python.exe"
  goto :show_python
)

for %%P in (python.exe) do (
  for /f "usebackq delims=" %%V in (`"%%~$PATH:P" -c "import sys; print('.'.join(map(str, sys.version_info[:2])))" 2^>nul`) do (
    if "%%V"=="3.12" set "PYEXE=%%~$PATH:P"
  )
)

:show_python
if defined PYEXE (
  for /f "usebackq delims=" %%V in (`"%PYEXE%" --version 2^>^&1`) do echo Encontrado: %%V
)
exit /b 0
