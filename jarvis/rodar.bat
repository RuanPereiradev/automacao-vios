@echo off
rem Jarvis no Windows: gera o relatorio mensal de processos por Grupo Cliente (jarvis\.env).
rem Pode dar dois cliques no arquivo ou rodar no terminal: .\rodar.bat
rem As planilhas ficam em saida\relatorios\(AAAA-MM). Outro grupo: .\rodar.bat --grupo "PLASFRAN CAMOCIM"
rem Teste rapido (so os 3 primeiros processos de cada grupo): .\rodar.bat --limite 3
rem O aviso "Error terminating service process" no fim e do Selenium no Windows e pode ser ignorado.
cd /d "%~dp0"
".venv\Scripts\python.exe" relatorio_processos.py .env %*
pause
