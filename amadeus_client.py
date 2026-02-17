"""
Amadeus API client for fetching flight prices.
Supports both live API calls and mock data generation for demo purposes.

Amadeus Self-Service API (free tier):
  - Flight Offers Search v2
  - Up to 500 free API calls per month in test environment
  - Sign up: https://developers.amadeus.com
"""

import httpx
import os
import random
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# One World alliance airline IATA codes
ONEWORLD_AIRLINES = [
    "AA", "BA", "CX", "AY", "IB", "JL", "MH", "QF", "QR", "AT", "RJ", "UL", "AS", "FJ"
]

# Which airlines typically fly which routes (realistic mapping)
ROUTE_AIRLINE_MAP = {
    ("LHR", "JFK"): ["BA", "AA", "AY", "IB", "QR"],
    ("JFK", "LHR"): ["BA", "AA", "AY", "IB", "QR"],
    ("LAX", "NRT"): ["AA", "JL", "QF", "CX"],
    ("NRT", "LAX"): ["JL", "AA", "QF", "CX"],
    ("SYD", "SIN"): ["QF", "BA", "MH", "CX"],
    ("SIN", "SYD"): ["QF", "BA", "MH", "CX"],
    ("LHR", "HKG"): ["BA", "CX", "QR", "AY"],
    ("HKG", "LHR"): ["CX", "BA", "QR", "AY"],
    ("DOH", "LHR"): ["QR", "BA"],
    ("LHR", "DOH"): ["QR", "BA"],
    ("JFK", "LAX"): ["AA", "AS", "JL"],
    ("LAX", "JFK"): ["AA", "AS", "JL"],
    ("MAD", "JFK"): ["IB", "AA", "BA"],
    ("JFK", "MAD"): ["IB", "AA", "BA"],
    ("HEL", "NRT"): ["AY", "JL"],
    ("NRT", "HEL"): ["AY", "JL"],
    ("SYD", "LAX"): ["QF", "AA", "CX", "JL"],
    ("LAX", "SYD"): ["QF", "AA", "CX", "JL"],
    ("LHR", "SYD"): ["BA", "QF", "QR", "CX", "MH"],
    ("SYD", "LHR"): ["QF", "BA", "QR", "CX", "MH"],
    ("AMM", "LHR"): ["RJ", "BA"],
    ("KUL", "NRT"): ["MH", "JL"],
    ("CMB", "SIN"): ["UL", "MH"],
    ("CMN", "JFK"): ["AT", "AA"],
}

# Base prices for routes (economy, one-way, in USD)
BASE_PRICES = {
    ("LHR", "JFK"): 450,
    ("JFK", "LHR"): 420,
    ("LAX", "NRT"): 680,
    ("NRT", "LAX"): 650,
    ("SYD", "SIN"): 380,
    ("SIN", "SYD"): 370,
    ("LHR", "HKG"): 620,
    ("HKG", "LHR"): 600,
    ("DOH", "LHR"): 380,
    ("LHR", "DOH"): 350,
    ("JFK", "LAX"): 180,
    ("LAX", "JFK"): 175,
    ("MAD", "JFK"): 420,
    ("JFK", "MAD"): 400,
    ("HEL", "NRT"): 580,
    ("NRT", "HEL"): 560,
    ("SYD", "LAX"): 780,
    ("LAX", "SYD"): 750,
    ("LHR", "SYD"): 950,
    ("SYD", "LHR"): 920,
    ("AMM", "LHR"): 340,
    ("KUL", "NRT"): 320,
    ("CMB", "SIN"): 180,
    ("CMN", "JFK"): 520,
}

# Airline price multipliers (some airlines are pricier than others)
AIRLINE_PRICE_MULTIPLIER = {
    "AA": 1.0,
    "BA": 1.15,
    "CX": 1.05,
    "AY": 0.95,
    "IB": 0.90,
    "JL": 1.10,
    "MH": 0.85,
    "QF": 1.12,
    "QR": 1.20,
    "AT": 0.80,
    "RJ": 0.82,
    "UL": 0.78,
    "AS": 0.88,
    "FJ": 0.92,
}


class AmadeusClient:
    """Client for Amadeus Self-Service API."""

    BASE_URL_TEST = "https://test.api.amadeus.com"
    BASE_URL_PROD = "https://api.amadeus.com"

    def __init__(self):
        self.api_key = os.getenv("AMADEUS_API_KEY", "")
        self.api_secret = os.getenv("AMADEUS_API_SECRET", "")
        self.env = os.getenv("AMADEUS_ENV", "test")
        self.use_mock = os.getenv("USE_MOCK_DATA", "true").lower() == "true"
        self.access_token = None
        self.token_expires_at = None

        if self.env == "production":
            self.base_url = self.BASE_URL_PROD
        else:
            self.base_url = self.BASE_URL_TEST

    async def _authenticate(self):
        """Authenticate with Amadeus API and get access token."""
        if self.access_token and self.token_expires_at and datetime.utcnow() < self.token_expires_at:
            return

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/security/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.api_key,
                    "client_secret": self.api_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code == 200:
                data = response.json()
                self.access_token = data["access_token"]
                self.token_expires_at = datetime.utcnow() + timedelta(
                    seconds=data.get("expires_in", 1799) - 60
                )
                logger.info("Amadeus authentication successful")
            else:
                logger.error(f"Amadeus auth failed: {response.status_code} {response.text}")
                raise Exception(f"Amadeus authentication failed: {response.status_code}")

    async def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None,
        adults: int = 1,
        cabin_class: str = "ECONOMY",
        max_results: int = 10,
    ) -> list:
        """
        Search for flight offers using Amadeus Flight Offers Search API.

        Args:
            origin: IATA airport code (e.g., 'LHR')
            destination: IATA airport code (e.g., 'JFK')
            departure_date: Date in YYYY-MM-DD format
            return_date: Optional return date
            adults: Number of adult passengers
            cabin_class: ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST
            max_results: Maximum number of results

        Returns:
            List of flight offer dicts with price and airline info
        """
        if self.use_mock or not self.api_key:
            return self._generate_mock_data(
                origin, destination, departure_date, return_date, cabin_class
            )

        try:
            await self._authenticate()
        except Exception as e:
            logger.warning(f"Amadeus auth failed: {e}. Falling back to mock data.")
            return self._generate_mock_data(
                origin, destination, departure_date, return_date, cabin_class
            )

        try:
            params = {
                "originLocationCode": origin,
                "destinationLocationCode": destination,
                "departureDate": departure_date,
                "adults": adults,
                "travelClass": cabin_class,
                "max": max_results,
                "currencyCode": "USD",
            }

            if return_date:
                params["returnDate"] = return_date

            # Filter for One World airlines
            params["includedAirlineCodes"] = ",".join(
                ROUTE_AIRLINE_MAP.get((origin, destination), ONEWORLD_AIRLINES[:5])
            )

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/v2/shopping/flight-offers",
                    params=params,
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    results = self._parse_amadeus_response(data)
                    if results:
                        return results
                    # Amadeus returned no results for this route — fall back to mock
                    logger.info(
                        f"Amadeus returned 0 results for {origin}-{destination}. Using mock data."
                    )
                    return self._generate_mock_data(
                        origin, destination, departure_date, return_date, cabin_class
                    )
                else:
                    logger.warning(
                        f"Amadeus API error: {response.status_code}. Falling back to mock data."
                    )
                    return self._generate_mock_data(
                        origin, destination, departure_date, return_date, cabin_class
                    )
        except Exception as e:
            logger.warning(f"Amadeus API request failed: {e}. Falling back to mock data.")
            return self._generate_mock_data(
                origin, destination, departure_date, return_date, cabin_class
            )

    def _parse_amadeus_response(self, data: dict) -> list:
        """Parse Amadeus API response into our format."""
        results = []
        offers = data.get("data", [])
        carrier_dict = data.get("dictionaries", {}).get("carriers", {})

        for offer in offers:
            price = float(offer.get("price", {}).get("total", 0))
            currency = offer.get("price", {}).get("currency", "USD")

            # Get the operating airline from the first segment
            segments = offer.get("itineraries", [{}])[0].get("segments", [])
            if segments:
                airline_code = segments[0].get("operating", {}).get(
                    "carrierCode", segments[0].get("carrierCode", "")
                )
            else:
                airline_code = ""

            # Only include One World airlines
            if airline_code in ONEWORLD_AIRLINES:
                results.append({
                    "airline_code": airline_code,
                    "airline_name": carrier_dict.get(airline_code, airline_code),
                    "price": price,
                    "currency": currency,
                    "cabin_class": offer.get("travelerPricings", [{}])[0]
                        .get("fareDetailsBySegment", [{}])[0]
                        .get("cabin", "ECONOMY"),
                    "departure_date": segments[0].get("departure", {}).get("at", "")[:10]
                        if segments else "",
                    "source": "amadeus",
                })

        return results

    def _generate_mock_data(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None,
        cabin_class: str = "ECONOMY",
    ) -> list:
        """Generate realistic mock flight price data."""
        route_key = (origin, destination)
        airlines = ROUTE_AIRLINE_MAP.get(route_key, random.sample(ONEWORLD_AIRLINES, 3))
        base_price = BASE_PRICES.get(route_key, random.randint(200, 800))

        results = []

        # Parse departure date to add seasonal variation
        try:
            dep_date = datetime.strptime(departure_date, "%Y-%m-%d")
            # Summer months (Jun-Aug) are more expensive
            month = dep_date.month
            if month in [6, 7, 8]:
                seasonal_factor = 1.3
            elif month in [12, 1]:  # Holiday season
                seasonal_factor = 1.25
            elif month in [3, 4]:  # Spring
                seasonal_factor = 1.1
            else:
                seasonal_factor = 1.0

            # How far out the departure is - closer dates are pricier
            days_out = (dep_date - datetime.utcnow()).days
            if days_out < 7:
                urgency_factor = 1.5
            elif days_out < 14:
                urgency_factor = 1.3
            elif days_out < 30:
                urgency_factor = 1.15
            elif days_out < 60:
                urgency_factor = 1.0
            else:
                urgency_factor = 0.9
        except ValueError:
            seasonal_factor = 1.0
            urgency_factor = 1.0

        # Cabin class multipliers
        cabin_multiplier = {
            "ECONOMY": 1.0,
            "PREMIUM_ECONOMY": 1.6,
            "BUSINESS": 3.2,
            "FIRST": 5.5,
        }.get(cabin_class, 1.0)

        for airline in airlines:
            airline_mult = AIRLINE_PRICE_MULTIPLIER.get(airline, 1.0)

            # Add some randomness to simulate real price variation
            random_factor = random.uniform(0.88, 1.15)

            price = round(
                base_price
                * airline_mult
                * seasonal_factor
                * urgency_factor
                * cabin_multiplier
                * random_factor,
                2,
            )

            results.append({
                "airline_code": airline,
                "airline_name": self._get_airline_name(airline),
                "price": price,
                "currency": "USD",
                "cabin_class": cabin_class,
                "departure_date": departure_date,
                "source": "mock",
            })

        return sorted(results, key=lambda x: x["price"])

    @staticmethod
    def _get_airline_name(code: str) -> str:
        """Get airline name from IATA code."""
        names = {
            "AA": "American Airlines",
            "BA": "British Airways",
            "CX": "Cathay Pacific",
            "AY": "Finnair",
            "IB": "Iberia",
            "JL": "Japan Airlines",
            "MH": "Malaysia Airlines",
            "QF": "Qantas",
            "QR": "Qatar Airways",
            "AT": "Royal Air Maroc",
            "RJ": "Royal Jordanian",
            "UL": "SriLankan Airlines",
            "AS": "Alaska Airlines",
            "FJ": "Fiji Airways",
        }
        return names.get(code, code)
