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
REM  1. Python 3.12
REM ----------------------------------------------------------------
echo.
echo [1/4] Verificando Python 3.12...

where winget >nul 2>&1
if errorlevel 1 (
  echo [ERRO] winget nao encontrado nesta maquina.
  echo        Atualize o Windows ou instale o "App Installer" da Microsoft Store.
  echo        Depois rode este script novamente.
  pause
  exit /b 1
)

set PYEXE=
where py >nul 2>&1
if not errorlevel 1 (
  py -3.12 --version >nul 2>&1
  if not errorlevel 1 (
    for /f "delims=" %%v in ('py -3.12 --version') do echo Encontrado: %%v
    set PYEXE=py -3.12
  )
)

if not defined PYEXE (
  echo Python 3.12 nao encontrado. Instalando via winget...
  winget install --id Python.Python.3.12 -e --source winget --accept-source-agreements --accept-package-agreements
  if errorlevel 1 (
    echo [ERRO] winget falhou ao instalar Python 3.12.
    echo        Instale manualmente em https://www.python.org/downloads/ e rode novamente.
    pause
    exit /b 1
  )
  echo Python 3.12 instalado.
  echo.
  echo [IMPORTANTE] Feche esta janela e abra novamente para o PATH atualizar,
  echo              depois rode setup.bat mais uma vez.
  pause
  exit /b 0
)

REM ----------------------------------------------------------------
REM  2. venv
REM ----------------------------------------------------------------
echo.
echo [2/4] Criando ambiente virtual em .\venv...

if exist "venv\Scripts\python.exe" (
  echo venv ja existe, reutilizando.
) else (
  %PYEXE% -m venv venv
  if errorlevel 1 (
    echo [ERRO] Falha ao criar venv.
    pause
    exit /b 1
  )
  echo venv criada.
)

venv\Scripts\python.exe -m pip install --upgrade pip wheel setuptools
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

set DLIB_URL=https://github.com/z-mahmud22/Dlib_Windows_Python3.x/raw/main/dlib-19.24.99-cp312-cp312-win_amd64.whl
set DLIB_FILE=%TEMP%\dlib-cp312-win_amd64.whl

if exist "%DLIB_FILE%" del "%DLIB_FILE%"

echo Baixando wheel do dlib...
curl -L --fail -o "%DLIB_FILE%" "%DLIB_URL%"
if errorlevel 1 (
  echo [ERRO] Falha ao baixar o wheel do dlib.
  echo        URL: %DLIB_URL%
  echo        Verifique sua conexao e tente novamente.
  pause
  exit /b 1
)

venv\Scripts\pip.exe install "%DLIB_FILE%"
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

venv\Scripts\pip.exe install -r requirements.txt
if errorlevel 1 (
  echo [ERRO] Falha ao instalar dependencias do requirements.txt.
  pause
  exit /b 1
)

REM Verificacao final
echo.
echo Verificando instalacao...
venv\Scripts\python.exe -c "import fastapi, uvicorn, cv2, face_recognition, PIL, numpy, win32api; print('OK - todos os modulos carregam')"
if errorlevel 1 (
  echo [AVISO] Alguns modulos falharam ao carregar. Veja a mensagem acima.
  pause
  exit /b 1
)

echo.
echo ============================================================
echo   Setup concluido com sucesso!
echo ============================================================
echo.
echo Para iniciar a aplicacao: duplo-clique em start.bat
echo.
echo Observacao: se a impressao abrir o visualizador em vez de
echo imprimir, rode docs\fix-print-apply.reg como administrador
echo (botao direito -^> Mesclar).
echo.
pause
endlocal
