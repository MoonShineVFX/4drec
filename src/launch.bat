@echo off
set LOGURU_LEVEL=INFO
cd /d %~dp0
%~dp0\.python\python %~dp0\main.py "%~1"
