# How to Start Redis

## Current Issue

Your system needs Redis to run the scheduler, but:
- Docker Desktop is not running
- No native Redis/Memurai service is installed

## Quick Fix - Start Docker Desktop

1. **Find Docker Desktop** in your Start Menu
2. **Click to start it** (it takes 30-60 seconds to start)
3. **Wait for the whale icon** to appear in your system tray
4. **Run LAUNCH.bat again**

The system will automatically start Redis in Docker.

## Alternative - Install Memurai (Redis for Windows)

If you don't want to use Docker:

### Option 1: Using winget (Recommended)
```powershell
winget install Memurai.Memurai-Developer
```

### Option 2: Manual Download
1. Go to: https://www.memurai.com/get-memurai
2. Download Memurai Developer (free)
3. Install it
4. It will start automatically as a Windows service
5. Run LAUNCH.bat again

## Verify Redis is Running

After starting Docker or installing Memurai, test the connection:

```powershell
python -c "import socket; s = socket.socket(); s.connect(('127.0.0.1', 6379)); print('Redis is running!'); s.close()"
```

If you see "Redis is running!" then you're good to go!

## Current Settings

- **Scraping interval:** 5 minutes (changed from 10 minutes)
- **Redis port:** 6379
- **Redis URL:** redis://127.0.0.1:6379/0

## What Happens Without Redis

Without Redis running:
- ❌ Scheduler won't work (no automatic scraping every 5 minutes)
- ❌ Celery worker will fail to start
- ✅ API still works (you can track products manually)
- ✅ Frontend still works (you can view data)
- ✅ Manual scraping still works (via "Track Product URL" button)

## After Redis is Running

Once Redis is running, restart the system:

```bash
# Stop everything first
STOP.bat

# Start everything again
LAUNCH.bat
```

The system will:
1. ✅ Connect to Redis successfully
2. ✅ Start Celery worker
3. ✅ Start Celery beat scheduler
4. ✅ Automatically scrape watchlist every 5 minutes
