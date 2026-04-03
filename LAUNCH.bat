@echo off
setlocal EnableExtensions

set "ROOT=%~dp0"
cd /d "%ROOT%"

set "API_HOST=127.0.0.1"
set "API_PORT=8000"
set "FRONTEND_HOST=127.0.0.1"
set "FRONTEND_PORT=3000"
set "REDIS_HOST=127.0.0.1"
set "REDIS_PORT=6379"
set "DATABASE_URL=sqlite+aiosqlite:///./artifacts/live_monitor.db"
set "MONGODB_URL="
set "REDIS_URL=redis://%REDIS_HOST%:%REDIS_PORT%/0"
set "FRONTEND_ORIGIN=http://%FRONTEND_HOST%:%FRONTEND_PORT%"
set "VITE_API_BASE_URL=http://%API_HOST%:%API_PORT%/api"
set "INGEST_API_URL=http://%API_HOST%:%API_PORT%"
set "DEFAULT_LOCATION=chennai-tn"
set "API_LOG=%ROOT%artifacts\launch_api.log"
set "FRONTEND_LOG=%ROOT%artifacts\launch_frontend.log"
set "CELERY_WORKER_LOG=%ROOT%artifacts\celery_worker.log"
set "CELERY_BEAT_LOG=%ROOT%artifacts\celery_beat.log"

if not exist "%ROOT%artifacts" mkdir "%ROOT%artifacts"

echo Checking Python...
python --version >nul 2>&1 || (
  echo Python is required and was not found on PATH.
  exit /b 1
)

echo Checking npm...
call npm.cmd --version >nul 2>&1 || (
  echo npm is required and was not found on PATH.
  exit /b 1
)

echo Checking Python packages...
python -c "import aiosqlite, fastapi, playwright, scrapy" >nul 2>&1 || (
  echo Installing Python dependencies...
  python -m pip install -e ".[dev]" || exit /b 1
)

if not exist "%ROOT%frontend\node_modules" (
  echo Installing frontend dependencies...
  pushd "%ROOT%frontend"
  call npm.cmd install || (
    popd
    exit /b 1
  )
  popd
)

call :ensure_api || exit /b 1
call :ensure_redis || exit /b 1
call :ensure_celery_worker || exit /b 1
call :ensure_celery_beat || exit /b 1
call :ensure_frontend || exit /b 1

set "MODE=%~1"
if /I "%MODE%"=="url" (
  set "TRACK_URL=%~2"
  set "TRACK_LOCATION=%~3"
  if "%TRACK_URL%"=="" (
    echo Usage: LAUNCH.bat url ^<amazon_product_url^> [location_code]
    exit /b 1
  )
  if "%TRACK_LOCATION%"=="" set "TRACK_LOCATION=%DEFAULT_LOCATION%"
  goto run_url
)
if /I "%MODE%"=="skip" goto open_browser

echo.
echo Choose startup mode:
echo   [U] Track a single Amazon product URL
echo   [S] Start app only
choice /C US /N /M "Selection: "
if errorlevel 2 goto open_browser
if errorlevel 1 goto prompt_url

:prompt_url
set /p TRACK_URL=Paste Amazon product URL: 
if "%TRACK_URL%"=="" goto open_browser
set /p TRACK_LOCATION=Buyer location code [%DEFAULT_LOCATION%]: 
if "%TRACK_LOCATION%"=="" set "TRACK_LOCATION=%DEFAULT_LOCATION%"
goto run_url

:run_url
echo Ensuring Playwright Chromium is installed...
python -m playwright install chromium || exit /b 1
echo Tracking live Amazon product...
set "TRACK_API=http://%API_HOST%:%API_PORT%"
python -c "import json, os, urllib.request; payload=json.dumps({'url': os.environ['TRACK_URL'], 'location_code': os.environ['TRACK_LOCATION']}).encode(); request=urllib.request.Request(os.environ['TRACK_API'] + '/api/track-url', data=payload, headers={'Content-Type': 'application/json'}); print(urllib.request.urlopen(request, timeout=420).read().decode())" || exit /b 1
goto open_browser

:open_browser
echo Opening dashboard...
start "" "http://%FRONTEND_HOST%:%FRONTEND_PORT%"
echo.
echo API: http://%API_HOST%:%API_PORT%
echo Dashboard: http://%FRONTEND_HOST%:%FRONTEND_PORT%
echo Redis: redis://%REDIS_HOST%:%REDIS_PORT%
echo Scheduler: Running (scrapes every 10 minutes)
echo Logs:
echo   %API_LOG%
echo   %FRONTEND_LOG%
echo   %CELERY_WORKER_LOG%
echo   %CELERY_BEAT_LOG%
echo.
echo You can also run:
echo   LAUNCH.bat url ^<amazon_product_url^>
echo   LAUNCH.bat skip
exit /b 0

:ensure_api
call :check_api
if not errorlevel 1 (
  echo API is already running on http://%API_HOST%:%API_PORT%.
  exit /b 0
)

call :port_listening %API_PORT%
if not errorlevel 1 (
  echo Port %API_PORT% is in use, but the API health check failed.
  echo Free port %API_PORT% or stop the conflicting process, then run LAUNCH.bat again.
  exit /b 1
)

echo Starting API on http://%API_HOST%:%API_PORT% ...
start "Bearing API" /min cmd /c "cd /d ""%ROOT%"" && set ""DATABASE_URL=%DATABASE_URL%"" && set ""MONGODB_URL=%MONGODB_URL%"" && set ""REDIS_URL=%REDIS_URL%"" && set ""FRONTEND_ORIGIN=%FRONTEND_ORIGIN%"" && set ""INGEST_API_URL=%INGEST_API_URL%"" && python -m uvicorn backend.app.main:app --host %API_HOST% --port %API_PORT% > ""%API_LOG%"" 2>&1"

for /L %%I in (1,1,60) do (
  call :check_api
  if not errorlevel 1 (
    echo API is ready.
    exit /b 0
  )
  timeout /t 1 /nobreak >nul
)

echo API did not become healthy in time.
if exist "%API_LOG%" type "%API_LOG%"
exit /b 1

:ensure_redis
call :check_redis
if not errorlevel 1 (
  echo Redis is already running on %REDIS_HOST%:%REDIS_PORT%.
  exit /b 0
)

echo Redis is not running. Attempting to start Redis automatically...

REM Check if Docker is available
docker --version >nul 2>&1
if errorlevel 1 (
  echo.
  echo Docker is not available. Redis is required for the scheduler to work.
  echo.
  echo Please install one of the following:
  echo   1. Docker Desktop: https://www.docker.com/products/docker-desktop
  echo   2. Memurai for Windows: https://www.memurai.com/get-memurai
  echo   3. Redis for Windows: https://github.com/tporadowski/redis/releases
  echo.
  echo After installation, run LAUNCH.bat again.
  echo.
  pause
  exit /b 1
)

REM Check if redis container already exists
docker ps -a --filter "name=bearing-monitor-redis" --format "{{.Names}}" | findstr /X "bearing-monitor-redis" >nul 2>&1
if not errorlevel 1 (
  echo Found existing Redis container. Starting it...
  docker start bearing-monitor-redis >nul 2>&1
) else (
  echo Creating new Redis container...
  docker run -d -p %REDIS_PORT%:6379 --name bearing-monitor-redis redis:latest >nul 2>&1
  if errorlevel 1 (
    echo Failed to start Redis container.
    echo Please check Docker is running and try again.
    pause
    exit /b 1
  )
)

REM Wait for Redis to be ready
echo Waiting for Redis to be ready...
for /L %%I in (1,1,30) do (
  call :check_redis
  if not errorlevel 1 (
    echo Redis is ready.
    exit /b 0
  )
  timeout /t 1 /nobreak >nul
)

echo Redis did not start in time.
echo Please check Docker logs: docker logs bearing-monitor-redis
pause
exit /b 1

:ensure_celery_worker
call :check_celery_worker
if not errorlevel 1 (
  echo Celery worker is already running.
  exit /b 0
)

echo Starting Celery worker...
start "Celery Worker" /min cmd /c "cd /d ""%ROOT%"" && set ""REDIS_URL=%REDIS_URL%"" && set ""DATABASE_URL=%DATABASE_URL%"" && set ""MONGODB_URL=%MONGODB_URL%"" && set ""INGEST_API_URL=%INGEST_API_URL%"" && python -m celery -A backend.app.celery_app worker --loglevel=info --pool=solo > ""%CELERY_WORKER_LOG%"" 2>&1"

for /L %%I in (1,1,30) do (
  call :check_celery_worker
  if not errorlevel 1 (
    echo Celery worker is ready.
    exit /b 0
  )
  timeout /t 1 /nobreak >nul
)

echo Celery worker did not start in time.
if exist "%CELERY_WORKER_LOG%" type "%CELERY_WORKER_LOG%"
exit /b 1

:ensure_celery_beat
call :check_celery_beat
if not errorlevel 1 (
  echo Celery beat scheduler is already running.
  exit /b 0
)

echo Starting Celery beat scheduler...
start "Celery Beat" /min cmd /c "cd /d ""%ROOT%"" && set ""REDIS_URL=%REDIS_URL%"" && set ""DATABASE_URL=%DATABASE_URL%"" && python -m celery -A backend.app.celery_app beat --loglevel=info > ""%CELERY_BEAT_LOG%"" 2>&1"

for /L %%I in (1,1,20) do (
  call :check_celery_beat
  if not errorlevel 1 (
    echo Celery beat scheduler is ready.
    exit /b 0
  )
  timeout /t 1 /nobreak >nul
)

echo Celery beat scheduler did not start in time.
if exist "%CELERY_BEAT_LOG%" type "%CELERY_BEAT_LOG%"
exit /b 1

:ensure_frontend
call :check_frontend
if not errorlevel 1 (
  echo Dashboard is already running on http://%FRONTEND_HOST%:%FRONTEND_PORT%.
  exit /b 0
)

call :port_listening %FRONTEND_PORT%
if not errorlevel 1 (
  echo Port %FRONTEND_PORT% is in use, but the dashboard check failed.
  echo Free port %FRONTEND_PORT% or stop the conflicting process, then run LAUNCH.bat again.
  exit /b 1
)

echo Building frontend...
pushd "%ROOT%frontend"
call npm.cmd run build || (
  popd
  exit /b 1
)
popd

echo Starting dashboard on http://%FRONTEND_HOST%:%FRONTEND_PORT% ...
start "Bearing Dashboard" /min cmd /c "cd /d ""%ROOT%frontend"" && set ""VITE_API_BASE_URL=%VITE_API_BASE_URL%"" && npm.cmd run preview -- --host %FRONTEND_HOST% --port %FRONTEND_PORT% > ""%FRONTEND_LOG%"" 2>&1"

for /L %%I in (1,1,60) do (
  call :check_frontend
  if not errorlevel 1 (
    echo Dashboard is ready.
    exit /b 0
  )
  timeout /t 1 /nobreak >nul
)

echo Dashboard did not become ready in time.
if exist "%FRONTEND_LOG%" type "%FRONTEND_LOG%"
exit /b 1

:check_api
python -c "import sys, urllib.request; urllib.request.urlopen('http://%API_HOST%:%API_PORT%/health', timeout=2); sys.exit(0)" >nul 2>&1
exit /b %errorlevel%

:check_redis
python -c "import sys; import socket; s = socket.socket(); s.settimeout(2); s.connect(('%REDIS_HOST%', %REDIS_PORT%)); s.close(); sys.exit(0)" >nul 2>&1
exit /b %errorlevel%

:check_celery_worker
python -c "import sys; from celery import Celery; app = Celery(broker='%REDIS_URL%'); stats = app.control.inspect().stats(); sys.exit(0 if stats else 1)" >nul 2>&1
exit /b %errorlevel%

:check_celery_beat
tasklist /FI "WINDOWTITLE eq Celery Beat" 2>nul | find /I "cmd.exe" >nul
exit /b %errorlevel%

:check_frontend
python -c "import sys, urllib.request; urllib.request.urlopen('http://%FRONTEND_HOST%:%FRONTEND_PORT%/', timeout=2); sys.exit(0)" >nul 2>&1
exit /b %errorlevel%

:port_listening
netstat -ano | findstr /R /C:":%~1 .*LISTENING" >nul
exit /b %errorlevel%
