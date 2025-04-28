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