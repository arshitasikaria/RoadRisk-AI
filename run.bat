@echo off
REM RoadRisk AI - one-click setup and run (Windows)
cd /d %~dp0
where python >nul 2>nul || (echo Python is not installed. Install Python 3.10+ from python.org and tick "Add Python to PATH". & pause & exit /b 1)
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)
call venv\Scripts\activate
echo Installing requirements (first run only, takes a few minutes)...
pip install -r requirements.txt
python manage.py migrate
python manage.py setup_project
echo.
echo ===== RoadRisk AI is starting at http://127.0.0.1:8000 =====
echo Logins:  admin/admin123   analyst/analyst123   public/public123
echo Press Ctrl+C in this window to stop the server.
echo.
start "" http://127.0.0.1:8000
python manage.py runserver
pause
