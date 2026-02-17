# SkyWatch — Flight Price Monitor

A web-based service that monitors flight prices from **oneworld alliance** airlines across major global routes. Prices update every hour via the Amadeus API.

![Python](https://img.shields.io/badge/Python-3.9+-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green) ![License](https://img.shields.io/badge/License-MIT-yellow)

## Features

- **Live Price Dashboard** — Real-time pricing grid across 24 global routes and 14 oneworld airlines
- **Price History & Trends** — Interactive charts showing price movements over time
- **Airline Comparison** — Side-by-side price comparison across airlines for any route
- **Price Alerts** — Set target prices and get notified when fares drop below your threshold
- **Hourly Updates** — Background scheduler fetches new prices every hour
- **Mock Data Mode** — Works out of the box without API keys for demos and development

## oneworld Alliance Airlines Tracked

| Code | Airline | Country |
|------|---------|---------|
| AA | American Airlines | United States |
| BA | British Airways | United Kingdom |
| CX | Cathay Pacific | Hong Kong |
| AY | Finnair | Finland |
| IB | Iberia | Spain |
| JL | Japan Airlines | Japan |
| MH | Malaysia Airlines | Malaysia |
| QF | Qantas | Australia |
| QR | Qatar Airways | Qatar |
| AT | Royal Air Maroc | Morocco |
| RJ | Royal Jordanian | Jordan |
| UL | SriLankan Airlines | Sri Lanka |
| AS | Alaska Airlines | United States |
| FJ | Fiji Airways | Fiji |

## Global Routes Monitored

Routes span six regions: Transatlantic, Transpacific, Asia-Pacific, Europe-Asia, Middle East-Europe, and US Domestic. Key routes include LHR-JFK, LAX-NRT, SYD-SIN, DOH-LHR, and more.

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/skywatch-flight-monitor.git
cd skywatch-flight-monitor
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your settings. To use **mock data** (no API key needed):

```
USE_MOCK_DATA=true
```

To use the **Amadeus API** (free tier — 500 calls/month):

1. Sign up at [developers.amadeus.com](https://developers.amadeus.com)
2. Create an app to get your API key and secret
3. Update `.env`:

```
AMADEUS_API_KEY=your_api_key_here
AMADEUS_API_SECRET=your_api_secret_here
USE_MOCK_DATA=false
AMADEUS_ENV=test
```

### 3. Run the application

```bash
python main.py
```

Or with uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Visit **http://localhost:8000** in your browser.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Main dashboard (web UI) |
| `GET` | `/api/dashboard` | Summary statistics |
| `GET` | `/api/airlines` | All oneworld airlines |
| `GET` | `/api/routes` | All monitored routes |
| `GET` | `/api/routes/regions` | Available regions |
| `GET` | `/api/prices/latest` | Latest prices (filterable) |
| `GET` | `/api/prices/history/{route_id}` | Price history |
| `GET` | `/api/prices/compare/{route_id}` | Airline price comparison |
| `POST` | `/api/prices/search` | Live flight search |
| `POST` | `/api/alerts` | Create price alert |
| `GET` | `/api/alerts` | List active alerts |
| `POST` | `/api/fetch-now` | Trigger manual price fetch |
| `GET` | `/api/health` | Health check |

## Architecture

```
skywatch-flight-monitor/
├── main.py              # FastAPI app, routes, lifecycle
├── database.py          # SQLite schema, queries, CRUD
├── amadeus_client.py    # Amadeus API + mock data engine
├── scheduler.py         # APScheduler hourly job
├── static/
│   └── index.html       # Single-page dashboard (Chart.js)
├── requirements.txt
├── .env.example
└── README.md
```

### Tech Stack

- **Backend**: Python 3.9+, FastAPI, uvicorn
- **Database**: SQLite (via aiosqlite)
- **Scheduling**: APScheduler (async)
- **Flight Data**: Amadeus Self-Service API
- **Frontend**: Vanilla JS, Chart.js
- **HTTP Client**: httpx (async)

## Development

### Running in development mode

```bash
uvicorn main:app --reload --port 8000
```

### Database

The SQLite database (`flight_monitor.db`) is created automatically on first run. To reset:

```bash
rm flight_monitor.db
python main.py
```

### Adding new routes

Edit the `global_routes` list in `database.py` and restart. The route-airline mapping in `amadeus_client.py` (`ROUTE_AIRLINE_MAP`) should also be updated.

## Deployment

### Docker (recommended)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AMADEUS_API_KEY` | *(empty)* | Amadeus API key |
| `AMADEUS_API_SECRET` | *(empty)* | Amadeus API secret |
| `AMADEUS_ENV` | `test` | `test` or `production` |
| `USE_MOCK_DATA` | `true` | Use mock data instead of API |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |

## Roadmap

- [ ] Email notification delivery for price alerts
- [ ] User accounts and saved preferences
- [ ] Business and First class monitoring
- [ ] Mobile-responsive progressive web app
- [ ] Redis caching for high-traffic deployment
- [ ] Historical price prediction (ML)
- [ ] Expand to Star Alliance and SkyTeam

## License

MIT License — see [LICENSE](LICENSE) for details.
