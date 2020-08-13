@echo off
set LOGURU_LEVEL=INFO
set PATH=%~dp0;%PATH%
cd /d %~dp0\app
%~dp0\.python\python %~dp0\app\main.py "%~1"
if NOT ["%errorlevel%"]==["0"] pause