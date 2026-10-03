@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  py -3.12 -m venv .venv
  if errorlevel 1 goto :error
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto :error
.venv\Scripts\python.exe -m streamlit run app.py
goto :eof
:error
echo No se pudo iniciar. Revisa que Python 3.12 este instalado y haya conexion a internet.
pause
