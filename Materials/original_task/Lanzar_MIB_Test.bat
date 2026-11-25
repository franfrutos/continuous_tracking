@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

set "CONDA_CMD="
where conda >nul 2>nul
if %ERRORLEVEL% EQU 0 set "CONDA_CMD=conda"
if not defined CONDA_CMD if exist "%USERPROFILE%\anaconda3\condabin\conda.bat" set "CONDA_CMD=%USERPROFILE%\anaconda3\condabin\conda.bat"
if not defined CONDA_CMD if exist "%USERPROFILE%\miniconda3\condabin\conda.bat" set "CONDA_CMD=%USERPROFILE%\miniconda3\condabin\conda.bat"
if not defined CONDA_CMD if exist "C:\ProgramData\anaconda3\condabin\conda.bat" set "CONDA_CMD=C:\ProgramData\anaconda3\condabin\conda.bat"
if not defined CONDA_CMD if exist "C:\ProgramData\miniconda3\condabin\conda.bat" set "CONDA_CMD=C:\ProgramData\miniconda3\condabin\conda.bat"

if not defined CONDA_CMD (
    echo No se ha encontrado conda.
    echo Instala Anaconda o Miniconda, o ajusta este lanzador a la ruta local de conda.
    pause
    exit /b 1
)

echo Iniciando la tarea MIB en modo test...
echo.

if /I "%CONDA_CMD%"=="conda" (
    call conda run --no-capture-output -n mib-psychopy python "%SCRIPT_DIR%run_mib_blocked.py" --mode test
) else (
    call "%CONDA_CMD%" run --no-capture-output -n mib-psychopy python "%SCRIPT_DIR%run_mib_blocked.py" --mode test
)

set "EXIT_CODE=%ERRORLEVEL%"
echo.
if "%EXIT_CODE%"=="0" (
    echo La tarea ha terminado correctamente.
) else (
    echo La tarea termino con error. Revisa el mensaje mostrado arriba.
)
pause
exit /b %EXIT_CODE%
