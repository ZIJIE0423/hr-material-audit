@echo off
cd /d "%~dp0"
python scripts\run_full.py
if errorlevel 1 (echo Failed. See details above.) else (echo Full local pipeline completed.)
pause
