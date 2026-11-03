@echo off
rem Relatorio de processos por Grupo Cliente com o segundo usuario do VIOS (.env.usuario2):
rem captura no VIOS (.txt e .json) e PDF do cliente numa execucao so (rodar_relatorio.py).
rem Pode dar dois cliques no arquivo ou rodar no terminal: .\rodar_usuario2.bat
rem Outro grupo: .\rodar_usuario2.bat --grupo "PAO MIX"
rem Opcoes da captura: --grupo, --sem-ficha, --sem-grupo, --encerrados. Do PDF: --ia, --refazer.
rem Os arquivos ficam em saida_usuario2\relatorios\(data) ou na RELATORIO_PASTA do .env.usuario2.
rem O aviso "Error terminating service process" no fim e do Selenium no Windows e pode ser ignorado.
rem Sai com 0 se os dois passos deram certo e 1 se algum falhou, para o Agendador de Tarefas saber.
rem No Agendador, definir a variavel SEM_PAUSA=1 (ou chamar o python direto) para nao parar no pause.
cd /d "%~dp0"
".venv\Scripts\python.exe" rodar_relatorio.py .env.usuario2 %*
set CODIGO=%ERRORLEVEL%
if not defined SEM_PAUSA pause
exit /b %CODIGO%
