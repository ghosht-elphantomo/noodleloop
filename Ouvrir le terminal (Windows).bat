@echo off
rem Ouvre le terminal sur cet ordinateur : petit serveur local (sans Internet), puis le navigateur.
cd /d "%~dp0"
set PORT=8765
where python >nul 2>nul
if %errorlevel%==0 (
  start "" /b python -m http.server %PORT% --bind 127.0.0.1
  goto ouvrir
)
where py >nul 2>nul
if %errorlevel%==0 (
  start "" /b py -m http.server %PORT% --bind 127.0.0.1
  goto ouvrir
)
start "" powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Minimized -File "%~dp0serveur.ps1" -Port %PORT%
:ouvrir
timeout /t 2 /nobreak >nul
start "" http://localhost:%PORT%/
echo Terminal ouvert sur http://localhost:%PORT%/  -  fermez cette fenetre pour l'arreter.
pause >nul
