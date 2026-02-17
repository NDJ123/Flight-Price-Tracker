"""
Background scheduler for hourly flight price fetching.
Uses APScheduler to run periodic price checks across all monitored routes.
"""

import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from amadeus_client import AmadeusClient
import database as db

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()
amadeus_client = AmadeusClient()


async def fetch_all_prices():
    """
    Fetch prices for all monitored routes from all applicable airlines.
    This runs every hour.
    """
    logger.info(f"Starting scheduled price fetch at {datetime.utcnow().isoformat()}")

    routes = await db.get_routes()
    total_fetched = 0
    errors = 0

    # Search for flights departing in 7, 14, 30, and 60 days
    search_windows = [7, 14, 30, 60]

    for route in routes:
        for days_ahead in search_windows:
            departure_date = (datetime.utcnow() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

            try:
                offers = await amadeus_client.search_flights(
                    origin=route["origin"],
                    destination=route["destination"],
                    departure_date=departure_date,
                    cabin_class="ECONOMY",
                )

                for offer in offers:
                    await db.save_price_snapshot(
                        route_id=route["id"],
                        airline_code=offer["airline_code"],
                        price=offer["price"],
                        currency=offer.get("currency", "USD"),
                        cabin_class=offer.get("cabin_class", "ECONOMY"),
                        departure_date=departure_date,
                        source=offer.get("source", "amadeus"),
                    )
                    total_fetched += 1

            except Exception as e:
                logger.error(
                    f"Error fetching prices for {route['origin']}-{route['destination']} "
                    f"(+{days_ahead}d): {e}"
                )
                errors += 1

    # Check alerts after fetching new prices
    try:
        triggered = await db.check_and_trigger_alerts()
        if triggered:
            logger.info(f"Triggered {len(triggered)} price alerts")
            for alert in triggered:
                logger.info(
                    f"  Alert: {alert['origin_city']}->{alert['destination_city']} "
                    f"hit ${alert['current_price']} (target: ${alert['target_price']})"
                )
    except Exception as e:
        logger.error(f"Error checking alerts: {e}")

    logger.info(
        f"Price fetch complete: {total_fetched} prices saved, {errors} errors"
    )
    return {"fetched": total_fetched, "errors": errors}


def start_scheduler():
    """Start the background scheduler with an hourly price fetch job."""
    scheduler.add_job(
        fetch_all_prices,
        "interval",
        hours=1,
        id="hourly_price_fetch",
        name="Hourly Flight Price Fetch",
        replace_existing=True,
        next_run_time=None,  # Don't run immediately; we trigger initial fetch separately
    )
    scheduler.start()
    logger.info("Background scheduler started - fetching prices every hour")


def stop_scheduler():
    """Stop the background scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Background scheduler stopped")
