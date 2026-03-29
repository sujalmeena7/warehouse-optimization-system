@echo off
title Warehouse Optimization System - Dev Server
cd /d "%~dp0"
echo.
echo ====================================================
echo   WAREHOUSE OPTIMIZATION SYSTEM - STARTUP
echo ====================================================
echo.
echo Installing dependencies for both backend and frontend...
echo.
echo [1/2] Backend dependencies...
cd backend
pip install -r requirements.txt --quiet
cd ..
echo [2/2] Frontend dependencies...
cd frontend
npm install --legacy-peer-deps --quiet
cd ..
echo.
echo ====================================================
echo   STARTING SERVERS
echo ====================================================
echo.
echo Backend: http://localhost:8000
echo Backend Docs: http://localhost:8000/docs
echo Frontend: http://localhost:3000
echo.
echo Press Ctrl+C to stop servers
echo.
start cmd /k "cd backend & python -m uvicorn server:app --host 0.0.0.0 --port 8000"
timeout /t 2 /nobreak
start cmd /k "cd frontend & npm start"
pause
