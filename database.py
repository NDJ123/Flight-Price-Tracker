"""
Database layer for the Flight Price Monitor.
Uses SQLite with aiosqlite for async operations.
Stores airlines, routes, price snapshots, price history, and user alerts.
"""

import aiosqlite
import os
from datetime import datetime, timedelta
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "flight_monitor.db")


async def get_db():
    """Get a database connection."""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def init_db():
    """Initialize database tables and seed data."""
    db = await get_db()
    try:
        # Create tables
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS airlines (
                iata_code TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                alliance TEXT DEFAULT 'oneworld',
                logo_url TEXT,
                country TEXT
            );

            CREATE TABLE IF NOT EXISTS routes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                origin TEXT NOT NULL,
                destination TEXT NOT NULL,
                origin_city TEXT,
                destination_city TEXT,
                region TEXT,
                UNIQUE(origin, destination)
            );

            CREATE TABLE IF NOT EXISTS price_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                route_id INTEGER NOT NULL,
                airline_code TEXT NOT NULL,
                price REAL NOT NULL,
                currency TEXT DEFAULT 'USD',
                cabin_class TEXT DEFAULT 'ECONOMY',
                departure_date TEXT,
                return_date TEXT,
                fetched_at TEXT NOT NULL DEFAULT (datetime('now')),
                source TEXT DEFAULT 'amadeus',
                FOREIGN KEY (route_id) REFERENCES routes(id),
                FOREIGN KEY (airline_code) REFERENCES airlines(iata_code)
            );

            CREATE TABLE IF NOT EXISTS price_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                route_id INTEGER NOT NULL,
                airline_code TEXT,
                target_price REAL NOT NULL,
                email TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                triggered_at TEXT,
                FOREIGN KEY (route_id) REFERENCES routes(id)
            );

            CREATE INDEX IF NOT EXISTS idx_snapshots_route ON price_snapshots(route_id);
            CREATE INDEX IF NOT EXISTS idx_snapshots_airline ON price_snapshots(airline_code);
            CREATE INDEX IF NOT EXISTS idx_snapshots_fetched ON price_snapshots(fetched_at);
            CREATE INDEX IF NOT EXISTS idx_snapshots_route_airline ON price_snapshots(route_id, airline_code);
        """)

        # Seed One World alliance airlines
        oneworld_airlines = [
            ("AA", "American Airlines", "oneworld", "United States"),
            ("BA", "British Airways", "oneworld", "United Kingdom"),
            ("CX", "Cathay Pacific", "oneworld", "Hong Kong"),
            ("AY", "Finnair", "oneworld", "Finland"),
            ("IB", "Iberia", "oneworld", "Spain"),
            ("JL", "Japan Airlines", "oneworld", "Japan"),
            ("MH", "Malaysia Airlines", "oneworld", "Malaysia"),
            ("QF", "Qantas", "oneworld", "Australia"),
            ("QR", "Qatar Airways", "oneworld", "Qatar"),
            ("AT", "Royal Air Maroc", "oneworld", "Morocco"),
            ("RJ", "Royal Jordanian", "oneworld", "Jordan"),
            ("UL", "SriLankan Airlines", "oneworld", "Sri Lanka"),
            ("AS", "Alaska Airlines", "oneworld", "United States"),
            ("FJ", "Fiji Airways", "oneworld", "Fiji"),
        ]

        for code, name, alliance, country in oneworld_airlines:
            await db.execute(
                """INSERT OR IGNORE INTO airlines (iata_code, name, alliance, country)
                   VALUES (?, ?, ?, ?)""",
                (code, name, alliance, country),
            )

        # Seed major global routes
        global_routes = [
            ("LHR", "JFK", "London Heathrow", "New York JFK", "Transatlantic"),
            ("JFK", "LHR", "New York JFK", "London Heathrow", "Transatlantic"),
            ("LAX", "NRT", "Los Angeles", "Tokyo Narita", "Transpacific"),
            ("NRT", "LAX", "Tokyo Narita", "Los Angeles", "Transpacific"),
            ("SYD", "SIN", "Sydney", "Singapore", "Asia-Pacific"),
            ("SIN", "SYD", "Singapore", "Sydney", "Asia-Pacific"),
            ("LHR", "HKG", "London Heathrow", "Hong Kong", "Europe-Asia"),
            ("HKG", "LHR", "Hong Kong", "London Heathrow", "Europe-Asia"),
            ("DOH", "LHR", "Doha", "London Heathrow", "Middle East-Europe"),
            ("LHR", "DOH", "London Heathrow", "Doha", "Middle East-Europe"),
            ("JFK", "LAX", "New York JFK", "Los Angeles", "US Domestic"),
            ("LAX", "JFK", "Los Angeles", "New York JFK", "US Domestic"),
            ("MAD", "JFK", "Madrid", "New York JFK", "Transatlantic"),
            ("JFK", "MAD", "New York JFK", "Madrid", "Transatlantic"),
            ("HEL", "NRT", "Helsinki", "Tokyo Narita", "Europe-Asia"),
            ("NRT", "HEL", "Tokyo Narita", "Helsinki", "Europe-Asia"),
            ("SYD", "LAX", "Sydney", "Los Angeles", "Transpacific"),
            ("LAX", "SYD", "Los Angeles", "Sydney", "Transpacific"),
            ("LHR", "SYD", "London Heathrow", "Sydney", "Europe-Oceania"),
            ("SYD", "LHR", "Sydney", "London Heathrow", "Europe-Oceania"),
            ("AMM", "LHR", "Amman", "London Heathrow", "Middle East-Europe"),
            ("KUL", "NRT", "Kuala Lumpur", "Tokyo Narita", "Asia"),
            ("CMB", "SIN", "Colombo", "Singapore", "Asia"),
            ("CMN", "JFK", "Casablanca", "New York JFK", "Africa-Americas"),
        ]

        for origin, dest, o_city, d_city, region in global_routes:
            await db.execute(
                """INSERT OR IGNORE INTO routes (origin, destination, origin_city, destination_city, region)
                   VALUES (?, ?, ?, ?, ?)""",
                (origin, dest, o_city, d_city, region),
            )

        await db.commit()
    finally:
        await db.close()


# ── Query functions ──────────────────────────────────────────────────────────


async def get_airlines():
    """Get all One World alliance airlines."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM airlines WHERE alliance = 'oneworld' ORDER BY name"
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def get_routes(region: Optional[str] = None):
    """Get monitored routes, optionally filtered by region."""
    db = await get_db()
    try:
        if region:
            cursor = await db.execute(
                "SELECT * FROM routes WHERE region = ? ORDER BY origin_city",
                (region,),
            )
        else:
            cursor = await db.execute("SELECT * FROM routes ORDER BY region, origin_city")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def get_route_regions():
    """Get distinct route regions."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT DISTINCT region FROM routes ORDER BY region")
        rows = await cursor.fetchall()
        return [row["region"] for row in rows]
    finally:
        await db.close()


async def save_price_snapshot(
    route_id: int,
    airline_code: str,
    price: float,
    currency: str = "USD",
    cabin_class: str = "ECONOMY",
    departure_date: str = None,
    return_date: str = None,
    source: str = "amadeus",
):
    """Save a new price snapshot."""
    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO price_snapshots
               (route_id, airline_code, price, currency, cabin_class,
                departure_date, return_date, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (route_id, airline_code, price, currency, cabin_class,
             departure_date, return_date, source),
        )
        await db.commit()
    finally:
        await db.close()


async def get_latest_prices(route_id: Optional[int] = None, airline_code: Optional[str] = None):
    """Get the most recent price for each route+airline combination."""
    db = await get_db()
    try:
        query = """
            SELECT ps.*, r.origin, r.destination, r.origin_city, r.destination_city,
                   r.region, a.name as airline_name
            FROM price_snapshots ps
            JOIN routes r ON ps.route_id = r.id
            JOIN airlines a ON ps.airline_code = a.iata_code
            WHERE ps.id IN (
                SELECT MAX(id) FROM price_snapshots
                GROUP BY route_id, airline_code
            )
        """
        params = []
        conditions = []

        if route_id:
            conditions.append("ps.route_id = ?")
            params.append(route_id)
        if airline_code:
            conditions.append("ps.airline_code = ?")
            params.append(airline_code)

        if conditions:
            query += " AND " + " AND ".join(conditions)

        query += " ORDER BY ps.price ASC"

        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def get_price_history(
    route_id: int,
    airline_code: Optional[str] = None,
    days: int = 30,
):
    """Get price history for a route over the specified number of days."""
    db = await get_db()
    try:
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        query = """
            SELECT ps.*, a.name as airline_name
            FROM price_snapshots ps
            JOIN airlines a ON ps.airline_code = a.iata_code
            WHERE ps.route_id = ? AND ps.fetched_at >= ?
        """
        params = [route_id, cutoff]

        if airline_code:
            query += " AND ps.airline_code = ?"
            params.append(airline_code)

        query += " ORDER BY ps.fetched_at ASC"

        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def get_price_comparison(route_id: int):
    """Compare latest prices across airlines for a specific route."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """
            SELECT ps.airline_code, a.name as airline_name, ps.price, ps.currency,
                   ps.cabin_class, ps.fetched_at, ps.departure_date,
                   r.origin, r.destination, r.origin_city, r.destination_city
            FROM price_snapshots ps
            JOIN airlines a ON ps.airline_code = a.iata_code
            JOIN routes r ON ps.route_id = r.id
            WHERE ps.route_id = ? AND ps.id IN (
                SELECT MAX(id) FROM price_snapshots
                WHERE route_id = ?
                GROUP BY airline_code
            )
            ORDER BY ps.price ASC
            """,
            (route_id, route_id),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def create_alert(route_id: int, target_price: float, email: str, airline_code: str = None):
    """Create a new price alert."""
    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO price_alerts (route_id, airline_code, target_price, email)
               VALUES (?, ?, ?, ?)""",
            (route_id, airline_code, target_price, email),
        )
        await db.commit()
    finally:
        await db.close()


async def get_active_alerts():
    """Get all active price alerts."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """
            SELECT pa.*, r.origin, r.destination, r.origin_city, r.destination_city
            FROM price_alerts pa
            JOIN routes r ON pa.route_id = r.id
            WHERE pa.is_active = 1
            ORDER BY pa.created_at DESC
            """
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def check_and_trigger_alerts():
    """Check if any price alerts should be triggered."""
    db = await get_db()
    triggered = []
    try:
        alerts = await get_active_alerts()
        for alert in alerts:
            # Get latest price for this route
            query = """
                SELECT MIN(ps.price) as lowest_price, ps.airline_code
                FROM price_snapshots ps
                WHERE ps.route_id = ? AND ps.id IN (
                    SELECT MAX(id) FROM price_snapshots
                    WHERE route_id = ?
                    GROUP BY airline_code
                )
            """
            params = [alert["route_id"], alert["route_id"]]

            if alert.get("airline_code"):
                query += " AND ps.airline_code = ?"
                params.append(alert["airline_code"])

            cursor = await db.execute(query, params)
            row = await cursor.fetchone()

            if row and row["lowest_price"] and row["lowest_price"] <= alert["target_price"]:
                # Trigger the alert
                await db.execute(
                    "UPDATE price_alerts SET triggered_at = datetime('now') WHERE id = ?",
                    (alert["id"],),
                )
                triggered.append({
                    **alert,
                    "current_price": row["lowest_price"],
                })

        await db.commit()
        return triggered
    finally:
        await db.close()


async def get_dashboard_stats():
    """Get summary statistics for the dashboard."""
    db = await get_db()
    try:
        stats = {}

        # Total routes monitored
        cursor = await db.execute("SELECT COUNT(*) as count FROM routes")
        row = await cursor.fetchone()
        stats["total_routes"] = row["count"]

        # Total airlines
        cursor = await db.execute("SELECT COUNT(*) as count FROM airlines")
        row = await cursor.fetchone()
        stats["total_airlines"] = row["count"]

        # Total price snapshots
        cursor = await db.execute("SELECT COUNT(*) as count FROM price_snapshots")
        row = await cursor.fetchone()
        stats["total_snapshots"] = row["count"]

        # Active alerts
        cursor = await db.execute("SELECT COUNT(*) as count FROM price_alerts WHERE is_active = 1")
        row = await cursor.fetchone()
        stats["active_alerts"] = row["count"]

        # Last update time
        cursor = await db.execute("SELECT MAX(fetched_at) as last_update FROM price_snapshots")
        row = await cursor.fetchone()
        stats["last_update"] = row["last_update"]

        # Cheapest current flight
        cursor = await db.execute("""
            SELECT ps.price, ps.currency, ps.airline_code, a.name as airline_name,
                   r.origin_city, r.destination_city
            FROM price_snapshots ps
            JOIN airlines a ON ps.airline_code = a.iata_code
            JOIN routes r ON ps.route_id = r.id
            WHERE ps.id IN (SELECT MAX(id) FROM price_snapshots GROUP BY route_id, airline_code)
            ORDER BY ps.price ASC
            LIMIT 1
        """)
        row = await cursor.fetchone()
        if row:
            stats["cheapest_flight"] = dict(row)

        return stats
    finally:
        await db.close()
