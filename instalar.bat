@echo off
chcp 65001 >nul
cd /d "%~dp0"
REM Rodar UMA VEZ, na primeira utilizacao: instala as bibliotecas necessarias.

where py >nul 2>nul
if %errorlevel%==0 (set "PY=py -3") else (set "PY=python")

%PY% --version >nul 2>nul
if errorlevel 1 (
  echo Python nao encontrado neste computador.
  echo Instale pelo site python.org e marque a opcao "Add python.exe to PATH".
  pause
  exit /b 1
)

echo Instalando as bibliotecas do relatorio...
%PY% -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo ERRO na instalacao. Tire um print desta tela e envie para o time de dados.
) else (
  echo.
  echo Instalacao concluida. Agora e so usar o rodar_relatorio.bat toda segunda-feira.
)
pause