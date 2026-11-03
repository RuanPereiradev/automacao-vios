@echo off
rem Roda o bot no Windows: rodar.bat (modo teste) ^| rodar.bat --confirmar (grava no VIOS)
cd /d "%~dp0"
.venv\Scripts\python.exe main.py %*
