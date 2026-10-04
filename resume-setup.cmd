@echo off
setlocal
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy RemoteSigned -File "%~dp0run.ps1" -Mode resume
pause
