@echo off
rem Gera o relatorio de processos por Grupo Cliente com o segundo usuario do VIOS (.env.usuario2).
rem Pode dar dois cliques no arquivo ou rodar no terminal: .\rodar_usuario2.bat
rem Os .txt ficam em saida_usuario2\relatorios\(data). Outro grupo: .\rodar_usuario2.bat --grupo "PAO MIX"
rem O aviso "Error terminating service process" no fim e do Selenium no Windows e pode ser ignorado.
cd /d "%~dp0"
".venv\Scripts\python.exe" relatorio_processos.py .env.usuario2 %*
pause
