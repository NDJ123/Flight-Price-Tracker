"""
Flight Price Monitor - Main Application
========================================
A web-based service that monitors flight prices from One World alliance airlines
across major global routes. Updates hourly via the Amadeus API.

Run with: uvicorn main:app --reload
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

import database as db
from scheduler import start_scheduler, stop_scheduler, fetch_all_prices
from email_service import send_alert_confirmation, is_configured as email_configured

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── App lifecycle ────────────────────────────────────────────────────────────


async def initial_fetch():
    """Run initial price fetch in the background."""
    try:
        logger.info("Running initial price fetch in background...")
        result = await fetch_all_prices()
        logger.info(f"Initial fetch complete: {result}")
    except Exception as e:
        logger.error(f"Initial fetch failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    logger.info("Starting Flight Price Monitor...")

    # Initialize database
    await db.init_db()
    logger.info("Database initialized")

    # Run initial price fetch in background (don't block startup)
    asyncio.create_task(initial_fetch())

    # Start hourly scheduler
    start_scheduler()

    yield

    # Shutdown
    stop_scheduler()
    logger.info("Flight Price Monitor stopped")


# ── FastAPI app ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="SkyWatch - Flight Price Monitor",
    description="Real-time flight price monitoring for One World alliance airlines",
    version="1.0.0",
    lifespan=lifespan,
)

# Serve static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ── Request/Response models ──────────────────────────────────────────────────


class AlertCreate(BaseModel):
    route_id: int
    target_price: float
    email: str
    airline_code: Optional[str] = None


class PriceSearchRequest(BaseModel):
    origin: str
    destination: str
    departure_date: str
    return_date: Optional[str] = None
    cabin_class: str = "ECONOMY"


# ── Routes ───────────────────────────────────────────────────────────────────


@app.get("/")
async def root():
    """Serve the main dashboard."""
    return FileResponse(os.path.join(static_dir, "index.html"))


@app.get("/api/dashboard")
async def get_dashboard():
    """Get dashboard summary statistics."""
    stats = await db.get_dashboard_stats()
    return {"status": "ok", "data": stats}


@app.get("/api/airlines")
async def get_airlines():
    """Get all monitored One World alliance airlines."""
    airlines = await db.get_airlines()
    return {"status": "ok", "data": airlines}


@app.get("/api/routes")
async def get_routes(region: Optional[str] = None):
    """Get all monitored routes, optionally filtered by region."""
    routes = await db.get_routes(region=region)
    return {"status": "ok", "data": routes}


@app.get("/api/routes/regions")
async def get_regions():
    """Get all available route regions."""
    regions = await db.get_route_regions()
    return {"status": "ok", "data": regions}


@app.get("/api/prices/latest")
async def get_latest_prices(
    route_id: Optional[int] = None,
    airline_code: Optional[str] = None,
):
    """Get the latest prices for routes and airlines."""
    prices = await db.get_latest_prices(route_id=route_id, airline_code=airline_code)
    return {"status": "ok", "data": prices}


@app.get("/api/prices/history/{route_id}")
async def get_price_history(
    route_id: int,
    airline_code: Optional[str] = None,
    days: int = Query(default=30, ge=1, le=365),
):
    """Get price history for a specific route."""
    history = await db.get_price_history(
        route_id=route_id,
        airline_code=airline_code,
        days=days,
    )
    return {"status": "ok", "data": history}


@app.get("/api/prices/compare/{route_id}")
async def get_price_comparison(route_id: int):
    """Compare prices across airlines for a specific route."""
    comparison = await db.get_price_comparison(route_id)
    return {"status": "ok", "data": comparison}


@app.post("/api/prices/search")
async def search_flights(request: PriceSearchRequest):
    """Search for live flight prices (triggers API call)."""
    from amadeus_client import AmadeusClient

    client = AmadeusClient()
    try:
        results = await client.search_flights(
            origin=request.origin,
            destination=request.destination,
            departure_date=request.departure_date,
            return_date=request.return_date,
            cabin_class=request.cabin_class,
        )
        return {"status": "ok", "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/alerts")
async def create_alert(alert: AlertCreate):
    """Create a new price alert."""
    await db.create_alert(
        route_id=alert.route_id,
        target_price=alert.target_price,
        email=alert.email,
        airline_code=alert.airline_code,
    )

    # Send confirmation email
    if email_configured():
        # Look up route details for the email
        routes = await db.get_routes()
        route = next((r for r in routes if r["id"] == alert.route_id), None)
        if route:
            send_alert_confirmation(
                to_email=alert.email,
                origin_city=route["origin_city"],
                destination_city=route["destination_city"],
                origin_code=route["origin"],
                destination_code=route["destination"],
                target_price=alert.target_price,
            )

    return {"status": "ok", "message": "Alert created successfully"}


@app.get("/api/alerts")
async def get_alerts():
    """Get all active price alerts."""
    alerts = await db.get_active_alerts()
    return {"status": "ok", "data": alerts}


@app.post("/api/fetch-now")
async def trigger_fetch():
    """Manually trigger a price fetch (for testing/admin)."""
    result = await fetch_all_prices()
    return {"status": "ok", "data": result}


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "SkyWatch Flight Price Monitor",
        "version": "1.0.0",
    }


# ── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=True)
