@echo off
cd /d "%~dp0frontend"
echo Installing frontend dependencies...
npm install --legacy-peer-deps --quiet
echo.
echo Starting Frontend Server on port 3000...
echo Open browser at: http://localhost:3000
echo.
npm start
pause
