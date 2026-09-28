@echo off
chcp 65001 >nul
cd /d "%~dp0"
REM Gera o relatorio semanal do funil. Uso normal: dois cliques neste arquivo.
REM Pelo Agendador de Tarefas do Windows: rodar_relatorio.bat agendado  (nao pausa no final)

if /i "%~1"=="agendado" (set "AGENDADO=1" & set "ARGS=") else (set "AGENDADO=" & set "ARGS=%*")

where py >nul 2>nul
if %errorlevel%==0 (set "PY=py -3") else (set "PY=python")

echo Gerando o relatorio semanal do funil...
echo.
%PY% relatorio_semanal.py %ARGS%
set "CODIGO=%errorlevel%"

echo.
if "%CODIGO%"=="0" (
  echo Relatorio gerado com sucesso: arquivos HTML, Excel e PDF na pasta "saida".
  if not defined AGENDADO start "" "%~dp0saida"
) else if "%CODIGO%"=="1" (
  echo ATENCAO: parte dos formatos nao foi gerada. Veja o log mais recente na pasta "logs".
  if not defined AGENDADO start "" "%~dp0saida"
) else (
  echo ERRO: o relatorio NAO foi gerado. Leia a mensagem acima ou o log mais recente na pasta "logs".
)

if not defined AGENDADO pause
exit /b %CODIGO%