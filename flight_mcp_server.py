"""
MCP Server for Flight Search and Booking.

This server exposes three tools via the Model Context Protocol:
  - search_flights: Search for available flights
  - get_flight_details: Get details for a specific flight
  - book_flight: Book a flight and receive a confirmation
"""

import json
import random
import string
from datetime import datetime, timedelta, timezone

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# ---------------------------------------------------------------------------
# Simulated flight data
# ---------------------------------------------------------------------------

AIRLINES = ["SkyAir", "CloudJet", "HorizonAir", "SwiftWings", "AzureFlights"]

FLIGHT_DB: dict[str, dict] = {}
BOOKINGS: dict[str, dict] = {}


def _generate_flights(origin: str, destination: str, date: str, passengers: int) -> list[dict]:
    """Generate a deterministic-ish list of simulated flights."""
    random.seed(f"{origin}{destination}{date}")
    flights = []
    for i in range(random.randint(2, 5)):
        flight_id = f"{origin[:2].upper()}{destination[:2].upper()}{date.replace('-', '')}{i+1:02d}"
        depart_hour = random.randint(5, 21)
        duration_min = random.randint(60, 600)
        depart_dt = datetime.strptime(date, "%Y-%m-%d").replace(hour=depart_hour, minute=random.choice([0, 15, 30, 45]))
        arrive_dt = depart_dt + timedelta(minutes=duration_min)
        price = round(random.uniform(80, 1200) * passengers, 2)
        airline = random.choice(AIRLINES)
        stops = 0 if duration_min < 180 else random.randint(1, 2)
        flight = {
            "flight_id": flight_id,
            "airline": airline,
            "origin": origin.upper(),
            "destination": destination.upper(),
            "date": date,
            "departure_time": depart_dt.strftime("%H:%M"),
            "arrival_time": arrive_dt.strftime("%H:%M"),
            "duration_minutes": duration_min,
            "stops": stops,
            "price_usd": price,
            "passengers": passengers,
            "seats_available": random.randint(1, 50),
        }
        FLIGHT_DB[flight_id] = flight
        flights.append(flight)
    return flights


# ---------------------------------------------------------------------------
# MCP Server definition
# ---------------------------------------------------------------------------

app = Server("flight-booking-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_flights",
            description=(
                "Search for available flights between two airports on a given date. "
                "Returns a list of flights with prices, times, and availability."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "origin": {
                        "type": "string",
                        "description": "Origin airport code or city name (e.g. 'JFK' or 'New York')",
                    },
                    "destination": {
                        "type": "string",
                        "description": "Destination airport code or city name (e.g. 'LAX' or 'Los Angeles')",
                    },
                    "date": {
                        "type": "string",
                        "description": "Travel date in YYYY-MM-DD format",
                    },
                    "passengers": {
                        "type": "integer",
                        "description": "Number of passengers (default: 1)",
                        "default": 1,
                    },
                },
                "required": ["origin", "destination", "date"],
            },
        ),
        Tool(
            name="get_flight_details",
            description="Retrieve detailed information about a specific flight using its flight ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "flight_id": {
                        "type": "string",
                        "description": "The unique flight identifier returned by search_flights",
                    },
                },
                "required": ["flight_id"],
            },
        ),
        Tool(
            name="book_flight",
            description=(
                "Book a specific flight for one or more passengers. "
                "Returns a booking confirmation with a reference number."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "flight_id": {
                        "type": "string",
                        "description": "The unique flight identifier to book",
                    },
                    "passenger_name": {
                        "type": "string",
                        "description": "Full name of the primary passenger",
                    },
                    "passenger_email": {
                        "type": "string",
                        "description": "Email address of the primary passenger",
                    },
                },
                "required": ["flight_id", "passenger_name", "passenger_email"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "search_flights":
        origin = arguments["origin"]
        destination = arguments["destination"]
        date = arguments["date"]
        passengers = arguments.get("passengers", 1)

        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return [TextContent(type="text", text=json.dumps({"error": "Invalid date format. Use YYYY-MM-DD."}))]

        flights = _generate_flights(origin, destination, date, passengers)
        result = {
            "search_results": {
                "origin": origin.upper(),
                "destination": destination.upper(),
                "date": date,
                "passengers": passengers,
                "flights_found": len(flights),
                "flights": flights,
            }
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "get_flight_details":
        flight_id = arguments["flight_id"]
        flight = FLIGHT_DB.get(flight_id)
        if not flight:
            return [TextContent(type="text", text=json.dumps({"error": f"Flight '{flight_id}' not found. Please search for flights first."}))]
        return [TextContent(type="text", text=json.dumps({"flight": flight}, indent=2))]

    elif name == "book_flight":
        flight_id = arguments["flight_id"]
        passenger_name = arguments["passenger_name"]
        passenger_email = arguments["passenger_email"]

        flight = FLIGHT_DB.get(flight_id)
        if not flight:
            return [TextContent(type="text", text=json.dumps({"error": f"Flight '{flight_id}' not found. Please search for flights first."}))]

        if flight["seats_available"] < 1:
            return [TextContent(type="text", text=json.dumps({"error": "No seats available on this flight."}))]

        confirmation_ref = "BK" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        booking = {
            "booking_reference": confirmation_ref,
            "status": "CONFIRMED",
            "flight_id": flight_id,
            "airline": flight["airline"],
            "origin": flight["origin"],
            "destination": flight["destination"],
            "date": flight["date"],
            "departure_time": flight["departure_time"],
            "arrival_time": flight["arrival_time"],
            "passenger_name": passenger_name,
            "passenger_email": passenger_email,
            "passengers": flight["passengers"],
            "total_price_usd": flight["price_usd"],
            "booked_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        BOOKINGS[confirmation_ref] = booking
        # Reduce available seats by the number of passengers booked
        seats_to_reserve = booking["passengers"]
        FLIGHT_DB[flight_id]["seats_available"] -= seats_to_reserve

        return [TextContent(type="text", text=json.dumps({"booking_confirmation": booking}, indent=2))]

    else:
        return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
