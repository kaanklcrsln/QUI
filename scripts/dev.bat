@echo off
rem Runs a command inside the QGIS environment with .venv\Scripts first on PATH.
rem Usage: scripts\dev.bat python -m pytest -q    |    scripts\dev.bat ruff check .
rem Override the QGIS install with:  set QGIS_ROOT=C:\Program Files\QGIS 3.xx.x
setlocal
if "%QGIS_ROOT%"=="" set "QGIS_ROOT=C:\Program Files\QGIS 3.40.3"
for %%G in (git.exe) do set "GIT_DIR_=%%~dp$PATH:G"
call "%QGIS_ROOT%\bin\o4w_env.bat"
path %~dp0..\.venv\Scripts;%QGIS_ROOT%\apps\qgis\bin;%PATH%;%GIT_DIR_%
set "QGIS_PREFIX_PATH=%QGIS_ROOT:\=/%/apps/qgis"
set "QT_PLUGIN_PATH=%QGIS_ROOT%\apps\qgis\qtplugins;%QGIS_ROOT%\apps\qt5\plugins"
set "PYTHONPATH=%QGIS_ROOT%\apps\qgis\python;%QGIS_ROOT%\apps\qgis\python\plugins"
%*
