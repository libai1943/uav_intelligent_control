@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  set "PYTHON=python"
) else (
  set "PYTHON=py -3"
)
if not exist .venv\Scripts\python.exe (
  %PYTHON% -m venv .venv
  if errorlevel 1 goto fail
)
.venv\Scripts\python.exe -c "import numpy, matplotlib" >nul 2>nul
if errorlevel 1 (
  .venv\Scripts\python.exe -m pip install -r requirements.txt
  if errorlevel 1 goto fail
)
set OPENBLAS_NUM_THREADS=1
set OMP_NUM_THREADS=1
.venv\Scripts\python.exe RunMe.py --profile book --parallel
if errorlevel 1 goto fail
echo Results saved to %cd%\outputs
pause
exit /b 0
:fail
echo Run failed. Check the error above. No successful experiment is claimed.
pause
exit /b 1
