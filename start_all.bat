@echo off
echo ======================================================
echo    Starting Smart News Aggregation System
echo ======================================================
echo.

:: Set working directory to the script location
cd /d "%~dp0"

:: Check Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found. Please install Python 3.8 or higher.
    goto :error
)

:: Check for required dependencies and install if missing
echo Checking and installing required packages...
cd backend
pip install -r requirements.txt
cd ..

:: Check for required services
echo Checking if RabbitMQ is running...
sc query RabbitMQ >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] RabbitMQ service not found. Make sure RabbitMQ is installed and running.
    echo Press any key to continue anyway or Ctrl+C to abort...
    pause >nul
)

:: Check if PostgreSQL is available (simple test)
echo Checking PostgreSQL connection...
python -c "import psycopg2; psycopg2.connect('postgresql://postgres:postgres@localhost:5432/news_aggregator').close()"
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] PostgreSQL connection failed. Make sure PostgreSQL is running.
    echo Press any key to continue anyway or Ctrl+C to abort...
    pause >nul
)

echo Starting RSS Feed Scrapers...
start cmd /c "title RSS Feed - Guardian && python RSS_Feeds\Guardian-RSS.py"
start cmd /c "title RSS Feed - FOX && python RSS_Feeds\FOX-RSS.py"
start cmd /c "title RSS Feed - Al-Jazeera && python RSS_Feeds\Al-Jazeera-RSS.py"
start cmd /c "title RSS Feed - LBC && python RSS_Feeds\LBC-RSS.py"
if exist RSS_Feeds\Guardian-MiddleEast-RSS.py (
    start cmd /c "title RSS Feed - Guardian Middle East && python RSS_Feeds\Guardian-MiddleEast-RSS.py"
)

:: Start the New York Times RSS feed scrapers
start cmd /c "title RSS Feed - NYT World && python RSS_Feeds\NYT-World-RSS.py"
start cmd /c "title RSS Feed - NYT Middle East && python RSS_Feeds\NYT-MiddleEast-RSS.py"
start cmd /c "title RSS Feed - NYT Business && python RSS_Feeds\NYT-Business-RSS.py"
start cmd /c "title RSS Feed - NYT Economy && python RSS_Feeds\NYT-Economy-RSS.py"
start cmd /c "title RSS Feed - NYT Media && python RSS_Feeds\NYT-MediaAndAdvertising-RSS.py"
start cmd /c "title RSS Feed - NYT Technology && python RSS_Feeds\NYT-Technology-RSS.py"
start cmd /c "title RSS Feed - NYT Personal Tech && python RSS_Feeds\NYT-PersonalTech-RSS.py"
start cmd /c "title RSS Feed - NYT Education && python RSS_Feeds\NYT-Education-RSS.py"
start cmd /c "title RSS Feed - NYT Europe && python RSS_Feeds\NYT-Europe-RSS.py"
start cmd /c "title RSS Feed - NYT Africa && python RSS_Feeds\NYT-Africa-RSS.py"
start cmd /c "title RSS Feed - NYT Americas && python RSS_Feeds\NYT-Americas-RSS.py"
start cmd /c "title RSS Feed - NYT Asia Pacific && python RSS_Feeds\NYT-AsiaPacific-RSS.py"

echo Starting NLP Processor...
start cmd /c "title NLP Processor && python NLP-Embeddings.py"

echo Starting Backend (FastAPI + RabbitMQ Consumer)...
start cmd /c "title Backend Server && cd backend && python run_backend.py"

:: Wait a bit to ensure backend is running before starting frontend
echo Waiting for backend to initialize...
ping -n 11 127.0.0.1 > nul
echo Backend initialization wait complete.

:: Start the React Native app
echo Starting React Native app...
start cmd /c "title React Native App && cd news-aggregator && npm start"

goto :summary

:summary
echo.
echo ======================================================
echo All components started successfully!
echo.
echo - RSS Feed Scrapers: Running in separate windows
echo - NLP Processor: Running in separate window
echo - Backend: Running in separate window
echo - React Native App: Running in separate window
echo.
echo Access the backend at: http://localhost:8000
echo For React Native app: Check the Expo console window
echo.
echo You can now see the print statements directly in each window
echo To stop all processes, close all opened command prompts
echo ======================================================

goto :end

:error
echo.
echo [ERROR] Failed to start all components. See error messages above.
pause

:end