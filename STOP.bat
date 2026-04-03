@echo off
setlocal EnableExtensions

echo Stopping Amazon Price Monitor services...
echo.

REM Stop Celery Beat
taskkill /FI "WINDOWTITLE eq Celery Beat" /F >nul 2>&1
if not errorlevel 1 (
  echo Stopped Celery Beat scheduler
) else (
  echo Celery Beat was not running
)

REM Stop Celery Worker
taskkill /FI "WINDOWTITLE eq Celery Worker" /F >nul 2>&1
if not errorlevel 1 (
  echo Stopped Celery Worker
) else (
  echo Celery Worker was not running
)

REM Stop API
taskkill /FI "WINDOWTITLE eq Bearing API" /F >nul 2>&1
if not errorlevel 1 (
  echo Stopped API server
) else (
  echo API server was not running
)

REM Stop Frontend
taskkill /FI "WINDOWTITLE eq Bearing Dashboard" /F >nul 2>&1
if not errorlevel 1 (
  echo Stopped Dashboard
) else (
  echo Dashboard was not running
)

echo.
echo All services stopped.
echo.
echo Note: Redis container is still running. To stop it:
echo   docker stop bearing-monitor-redis
echo.
echo To stop and remove Redis container:
echo   docker stop bearing-monitor-redis
echo   docker rm bearing-monitor-redis
echo.
pause
