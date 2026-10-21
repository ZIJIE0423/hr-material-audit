@echo off
cd /d "%~dp0"
python scripts\run_project.py
if errorlevel 1 (echo Execution failed. See error above.) else (echo Local outputs ready. Feishu sync and messaging were not executed.)
pause
