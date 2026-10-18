#!/usr/bin/env bash
# RoadRisk AI - one-command setup and run (macOS / Linux)
cd "$(dirname "$0")"
[ -d venv ] || python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py setup_project
echo
echo "===== RoadRisk AI is starting at http://127.0.0.1:8000 ====="
echo "Logins: admin/admin123  analyst/analyst123  public/public123"
python manage.py runserver
