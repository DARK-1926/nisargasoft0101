# System Architecture - Simple Overview

## How It All Works

```
┌─────────────────────────────────────────────────────────────┐
│                        LAUNCH.bat                            │
│                    (One Command Start)                       │
└────────────┬────────────────────────────────────────────────┘
             │
             ├──> Checks Python & Node.js installed
             ├──> Installs dependencies automatically
             ├──> Starts Redis (Docker or native)
             │
             ├──> Starts 5 Services:
             │    ┌─────────────────────────────────────────┐
             │    │ 1. API Server (FastAPI)                 │
             │    │    - Port 8000                          │
             │    │    - REST endpoints                     │
             │    │    - Real-time updates (SSE)            │
             │    └─────────────────────────────────────────┘
             │    ┌─────────────────────────────────────────┐
             │    │ 2. Redis (Message Broker)               │
             │    │    - Port 6379                          │
             │    │    - Task queue                         │
             │    │    - Automatic via Docker               │
             │    └─────────────────────────────────────────┘
             │    ┌─────────────────────────────────────────┐
             │    │ 3. Celery Worker (Task Executor)        │
             │    │    - Runs scraping tasks                │
             │    │    - Processes queue                    │
             │    └─────────────────────────────────────────┘
             │    ┌─────────────────────────────────────────┐
             │    │ 4. Celery Beat (Scheduler)              │
             │    │    - Triggers tasks every 10 min        │
             │    │    - Automatic monitoring               │
             │    └─────────────────────────────────────────┘
             │    ┌─────────────────────────────────────────┐
             │    │ 5. Frontend (React + Vite)              │
             │    │    - Port 3000                          │
             │    │    - Dashboard UI                       │
             │    └─────────────────────────────────────────┘
             │
             └──> Opens browser to http://127.0.0.1:3000
```

## Automatic Monitoring Flow

```
Every 10 Minutes:
┌──────────────────┐
│  Celery Beat     │  Triggers scheduled task
│  (Scheduler)     │
└────────┬─────────┘
         │
         v
┌──────────────────┐
│  Celery Worker   │  Executes scraping task
│  (Task Executor) │
└────────┬─────────┘
         │
         v
┌──────────────────┐
│  Scraper         │  For each watchlist item:
│  (Scrapy +       │  1. Navigate to Amazon
│   Playwright)    │  2. Set location (5 cities)
│                  │  3. Scroll to load ALL sellers
│                  │  4. Extract offers
└────────┬─────────┘
         │
         v
┌──────────────────┐
│  API Server      │  1. Store in database
│  (FastAPI)       │  2. Check for price drops
│                  │  3. Generate alerts
│                  │  4. Notify via SSE
└────────┬─────────┘
         │
         v
┌──────────────────┐
│  Frontend        │  1. Receive real-time update
│  (React)         │  2. Update price graphs
│                  │  3. Show new alerts
└──────────────────┘
```

## Data Flow - User Tracks Product

```
User Action:
┌──────────────────┐
│  User pastes     │
│  Amazon URL      │
└────────┬─────────┘
         │
         v
┌──────────────────┐
│  Frontend        │  POST /api/track-url
│  (React)         │
└────────┬─────────┘
         │
         v
┌──────────────────┐
│  API Server      │  1. Validate URL
│  (FastAPI)       │  2. Extract ASIN
│                  │  3. Trigger immediate scrape
└────────┬─────────┘
         │
         v
┌──────────────────┐
│  Scraper         │  1. Navigate to product page
│  (Scrapy +       │  2. Set buyer location
│   Playwright)    │  3. Go to offer listing
│                  │  4. Scroll to load ALL sellers
│                  │  5. Extract all offers
└────────┬─────────┘
         │
         v
┌──────────────────┐
│  API Server      │  POST /api/ingest
│  (FastAPI)       │  1. Store product
│                  │  2. Store sellers
│                  │  3. Store offers with timestamp
└────────┬─────────┘
         │
         v
┌──────────────────┐
│  Database        │  SQLite (local) or PostgreSQL
│  (SQLite/        │  - products table
│   PostgreSQL)    │  - sellers table
│                  │  - offers table (time-series)
│                  │  - watchlist table
│                  │  - alerts table
└────────┬─────────┘
         │
         v
┌──────────────────┐
│  Frontend        │  1. Display current offers
│  (React)         │  2. Show price graph
│                  │  3. List all sellers
└──────────────────┘
```

## Multi-Location Support

```
For Each Watchlist Item:
┌──────────────────────────────────────────────────────────┐
│  Scraper runs for ALL 5 locations:                       │
│                                                           │
│  1. Chennai, Tamil Nadu (600001)                         │
│     └─> Set PIN code, scrape, store with location tag   │
│                                                           │
│  2. Mumbai, Maharashtra (400001)                         │
│     └─> Set PIN code, scrape, store with location tag   │
│                                                           │
│  3. Bengaluru, Karnataka (560001)                        │
│     └─> Set PIN code, scrape, store with location tag   │
│                                                           │
│  4. Delhi, Delhi (110001)                                │
│     └─> Set PIN code, scrape, store with location tag   │
│                                                           │
│  5. Hyderabad, Telangana (500001)                        │
│     └─> Set PIN code, scrape, store with location tag   │
└──────────────────────────────────────────────────────────┘

Result: Separate price history per location per seller
```

## Seller Capture - The Fix

```
Before Fix:
┌──────────────────┐
│  Amazon Page     │  28 sellers total
│  Loads           │  Only 11 visible initially
└────────┬─────────┘
         │
         v
┌──────────────────┐
│  Scraper         │  Extracts only visible offers
│  (Old)           │  Result: 11/28 sellers captured ❌
└──────────────────┘

After Fix:
┌──────────────────┐
│  Amazon Page     │  28 sellers total
│  Loads           │  Only 11 visible initially
└────────┬─────────┘
         │
         v
┌──────────────────┐
│  Scraper         │  1. Wait for page ready
│  (New)           │  2. Scroll to bottom
│                  │  3. Wait for new offers to load
│                  │  4. Click "Show more" if present
│                  │  5. Repeat until no new offers
│                  │  6. Extract ALL offers
│                  │  Result: 28/28 sellers captured ✅
└──────────────────┘
```

## Price History Tracking

```
Time: 10:00 AM
┌──────────────────┐
│  Scrape Run #1   │  Seller A: ₹1000
│                  │  Seller B: ₹1050
│                  │  Seller C: ₹980
└────────┬─────────┘
         │
         v
┌──────────────────┐
│  Database        │  Store with timestamp
└──────────────────┘

Time: 10:10 AM (10 minutes later)
┌──────────────────┐
│  Scrape Run #2   │  Seller A: ₹1000 (no change)
│                  │  Seller B: ₹1020 (dropped ₹30)
│                  │  Seller C: ₹980 (no change)
└────────┬─────────┘
         │
         v
┌──────────────────┐
│  Database        │  Store with new timestamp
└────────┬─────────┘
         │
         v
┌──────────────────┐
│  Alert Engine    │  Seller B dropped 2.9%
│                  │  Generate alert if > threshold
└────────┬─────────┘
         │
         v
┌──────────────────┐
│  Frontend        │  Update graph showing price drop
│                  │  Display alert notification
└──────────────────┘
```

## Technology Stack

```
Frontend:
├─ React 18
├─ TypeScript
├─ TanStack Query (data fetching)
├─ Chart.js (price graphs)
└─ Vite (build tool)

Backend:
├─ FastAPI (API framework)
├─ SQLAlchemy (ORM)
├─ Pydantic (validation)
├─ Celery (task queue)
└─ Redis (message broker)

Scraper:
├─ Scrapy (crawling framework)
├─ Playwright (browser automation)
├─ Rotating proxies (anti-blocking)
└─ Location simulation

Database:
├─ SQLite (local development)
└─ PostgreSQL/TimescaleDB (production)

Deployment:
├─ Docker (containerization)
├─ Docker Compose (orchestration)
└─ LAUNCH.bat (Windows quick start)
```

## File Structure

```
project/
├── LAUNCH.bat              # One-command start
├── STOP.bat                # Stop all services
├── QUICKSTART.md           # Quick start guide
│
├── backend/
│   ├── app/
│   │   ├── main.py         # FastAPI app
│   │   ├── celery_app.py   # Celery configuration
│   │   ├── tasks.py        # Scheduled tasks
│   │   ├── routes.py       # API endpoints
│   │   ├── models.py       # Database models
│   │   └── services/       # Business logic
│   │       ├── watchlist.py
│   │       ├── market_data.py
│   │       └── alerts.py
│   └── tests/              # Backend tests
│
├── scraper/
│   ├── amazon_monitor/
│   │   ├── spiders/
│   │   │   └── amazon_bearings.py  # Main spider
│   │   ├── middlewares.py          # Proxy rotation
│   │   └── runner.py               # CLI runner
│   └── tests/              # Scraper tests
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx         # Main component
│   │   ├── api.ts          # API client
│   │   └── types.ts        # TypeScript types
│   └── package.json        # Node dependencies
│
├── artifacts/              # Logs and failures
│   ├── launch_api.log
│   ├── celery_worker.log
│   ├── celery_beat.log
│   └── scraper_failures/   # Screenshots
│
└── scripts/
    ├── verify_fixes.py     # Verification script
    └── seed_demo_data.py   # Demo data generator
```

## Key Features

1. **Automatic Monitoring**
   - Scrapes every 10 minutes
   - No manual intervention needed
   - Runs in background

2. **Complete Data Capture**
   - Scrolls to load all sellers
   - Handles pagination
   - Captures all offers

3. **Multi-Location Support**
   - 5 Indian cities
   - Location-specific pricing
   - Buy Box per location

4. **Real-Time Updates**
   - Server-Sent Events (SSE)
   - Live price updates
   - Instant alerts

5. **Price History**
   - Per-seller tracking
   - Time-series data
   - Interactive graphs

6. **Smart Alerts**
   - Configurable thresholds
   - Slack/email notifications
   - Competitor undercut detection

7. **Easy Deployment**
   - One command start
   - Automatic dependency installation
   - Docker integration
