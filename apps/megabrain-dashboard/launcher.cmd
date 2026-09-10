@echo off
setlocal
set "ROOT=%~dp0"
"%ROOT%..\ia-quota-widget\.venv\Scripts\pythonw.exe" "%ROOT%dashboard.py" %*
