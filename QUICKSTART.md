# Quick Start Guide

## One Command to Rule Them All

```bash
LAUNCH.bat
```

That's it! Everything else is automatic.

## What Happens Automatically

When you run `LAUNCH.bat`, it will:

1. ✅ Check if Python and npm are installed
2. ✅ Install Python dependencies (if needed)
3. ✅ Install Node.js dependencies (if needed)
4. ✅ Check if Redis is running
5. ✅ **Start Redis automatically in Docker** (if Docker is available)
6. ✅ Start API server
7. ✅ Start Celery worker (task execution)
8. ✅ Start Celery beat (scheduler - scrapes every 10 minutes)
9. ✅ Build and start frontend
10. ✅ Open browser to dashboard

## Prerequisites

### Required

- **Python 3.9+** - [Download](https://www.python.org/downloads/)
- **Node.js 16+** - [Download](https://nodejs.org/)

### For Automatic Redis Setup (Recommended)

- **Docker Desktop** - [Download](https://www.docker.com/products/docker-desktop)

If you have Docker, Redis will start automatically. No manual setup needed!

### Alternative: Manual Redis Setup

If you don't want to use Docker, install Redis natively:

**Option 1: Memurai (Recommended for Windows)**
- Download: https://www.memurai.com/get-memurai
- Install and it runs as a Windows service

**Option 2: Redis for Windows**
- Download: https://github.com/tporadowski/redis/releases
- Install the `.msi` file

## First Time Setup

1. **Clone or download this project**

2. **If using Docker (Recommended):**
   - Install Docker Desktop
   - Start Docker Desktop
   - Run `LAUNCH.bat`
   - Done!

3. **If not using Docker:**
   - Install Memurai or Redis for Windows
   - Run `LAUNCH.bat`
   - Done!

## Stopping the System

```bash
STOP.bat
```

This stops all services but keeps Redis running for next time.

## What You Get

### Dashboard
- **URL:** http://127.0.0.1:3000
- Track any Amazon product
- Monitor prices across 5 Indian cities
- View price history graphs per seller
- Get alerts for price drops

### API
- **URL:** http://127.0.0.1:8000
- **Docs:** http://127.0.0.1:8000/docs
- RESTful API for all operations
- Real-time updates via Server-Sent Events

### Automatic Monitoring
- Scrapes every 10 minutes
- Tracks all watchlist items
- Updates price history automatically
- Generates alerts for significant price drops

### Multi-Location Support
All 5 locations are now available:
- Chennai, Tamil Nadu (600001)
- Mumbai, Maharashtra (400001)
- Bengaluru, Karnataka (560001)
- Delhi, Delhi (110001)
- Hyderabad, Telangana (500001)

## Verify Everything Works

```bash
python scripts/verify_fixes.py
```

Expected output:
```
✓ Redis is running
✓ API is running
✓ /api/locations returns all 5 locations
✓ Celery worker is running
✓ All checks passed!
```

## Common Issues

### "Docker is not available"

**You see this if Docker isn't installed or running.**

**Solution 1 (Recommended):** Install Docker
- Download Docker Desktop
- Install and start it
- Run `LAUNCH.bat` again

**Solution 2:** Install Redis natively
- Install Memurai or Redis for Windows
- Run `LAUNCH.bat` again

### "Failed to start Redis container"

**Docker is installed but Redis won't start.**

**Solution:**
1. Make sure Docker Desktop is running
2. Check Docker works: `docker ps`
3. Try manually: `docker run -d -p 6379:6379 --name bearing-monitor-redis redis:latest`
4. Run `LAUNCH.bat` again

### Port Already in Use

**Another service is using port 8000 or 3000.**

**Solution:**
1. Stop the conflicting service
2. Or edit `LAUNCH.bat` to use different ports:
   - Change `API_PORT=8000` to another port
   - Change `FRONTEND_PORT=3000` to another port

## Usage

### Track a Product

1. Open http://127.0.0.1:3000
2. Paste an Amazon product URL
3. Select a location
4. Click "Track Product URL"
5. Product is added and scraped immediately

### Add to Watchlist

1. After tracking a product, click "Add to Watchlist"
2. The scheduler will now scrape it every 10 minutes
3. Price history builds up automatically
4. Graphs show trends over time

### Search for Products

1. Enter a search query (e.g., "SKF bearing 6205")
2. Select a location
3. Click "Discover Products"
4. Add interesting products to watchlist

### Monitor Prices

- Dashboard shows current prices for all sellers
- Graphs show price history per seller
- Alerts appear when competitors undercut your prices
- Data updates automatically every 10 minutes

## Deployment to Other Machines

### Copy and Run

1. Copy the entire project folder
2. Make sure target machine has:
   - Python 3.9+
   - Node.js 16+
   - Docker Desktop (or native Redis)
3. Run `LAUNCH.bat`
4. Everything installs and starts automatically!

**No manual configuration needed!**

## Logs

If something goes wrong, check these logs:

- `artifacts/launch_api.log` - API server
- `artifacts/celery_worker.log` - Task execution
- `artifacts/celery_beat.log` - Scheduler
- `artifacts/launch_frontend.log` - Frontend
- `artifacts/scraper_failures/` - Failed scrapes with screenshots

## Configuration

Edit `.env` file to customize:

```env
# Scraping interval (minutes)
SCRAPE_INTERVAL_MINUTES=10

# Locations to monitor
DEFAULT_LOCATIONS=chennai-tn,mumbai-mh,bengaluru-ka,delhi-dl,hyderabad-ts

# Your seller names (for alerts)
OWN_SELLER_NAMES=Your Company Name

# Price drop threshold for alerts (10% = 0.10)
PRICE_DROP_THRESHOLD=0.10

# Slack webhook for notifications (optional)
SLACK_WEBHOOK_URL=

# Email settings (optional)
ALERT_EMAIL_FROM=
ALERT_EMAIL_TO=
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
```

## What's Fixed

This version includes fixes for:

1. ✅ **Scheduler now runs automatically** - No more manual scraping
2. ✅ **All sellers captured** - Scraper scrolls to load all offers
3. ✅ **All locations visible** - Dropdown shows all 5 cities
4. ✅ **Automatic Redis setup** - Starts in Docker if available

## Need Help?

1. Run verification: `python scripts/verify_fixes.py`
2. Check logs in `artifacts/` folder
3. Review detailed docs: `.kiro/specs/scheduler-and-data-collection-fixes/IMPLEMENTATION_SUMMARY.md`

## Next Steps

- Add products to watchlist
- Wait 10 minutes for first automatic scrape
- Watch price history graphs build up
- Set up Slack/email alerts for price drops
- Monitor competitor pricing across all locations
