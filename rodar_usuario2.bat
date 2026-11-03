@echo off
rem Gera o relatorio mensal de processos por Grupo Cliente com o segundo usuario do VIOS (.env.usuario2).
rem Pode dar dois cliques no arquivo ou rodar no terminal: .\rodar_usuario2.bat
rem As planilhas ficam em saida_usuario2\relatorios\(AAAA-MM). Outro grupo: .\rodar_usuario2.bat --grupo "PLASFRAN CAMOCIM"
rem Teste rapido (so os 3 primeiros processos de cada grupo): .\rodar_usuario2.bat --limite 3
rem O aviso "Error terminating service process" no fim e do Selenium no Windows e pode ser ignorado.
cd /d "%~dp0"
".venv\Scripts\python.exe" relatorio_processos.py .env.usuario2 %*
pause
