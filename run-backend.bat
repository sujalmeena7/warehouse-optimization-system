@echo off
cd /d "%~dp0backend"
echo Installing backend dependencies...
pip install -r requirements.txt --quiet
echo.
echo Starting Backend Server on port 8000...
echo Open browser at: http://localhost:8000/docs
echo.
python -m uvicorn server:app --host 0.0.0.0 --port 8000
pause
