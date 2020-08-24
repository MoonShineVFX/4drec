@echo off
set PYTHONPATH=%~dp0;%PYTHONPATH%
set PATH=%~dp0;%PATH%
cd /d %~dp0\resolve
%~dp0\.python\python -u %~dp0\resolve\launch.py %*
if NOT ["%errorlevel%"]==["0"] pause