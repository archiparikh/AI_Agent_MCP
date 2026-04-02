"""
Tests for the Flight MCP Server and Agent utilities.

These tests exercise the flight simulation logic and tool conversion
without requiring a live Anthropic API key.
"""

import asyncio
import json
import sys
import os
import pytest

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import flight_mcp_server as server_module
from flight_mcp_server import _generate_flights, FLIGHT_DB, BOOKINGS, app, call_tool
from agent import mcp_tool_to_anthropic


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def run_async(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# _generate_flights
# ---------------------------------------------------------------------------

class TestGenerateFlights:
    def test_returns_list(self):
        flights = _generate_flights("JFK", "LAX", "2025-06-15", 1)
        assert isinstance(flights, list)
        assert len(flights) >= 2

    def test_flight_fields_present(self):
        flights = _generate_flights("JFK", "LAX", "2025-06-15", 1)
        required = {
            "flight_id", "airline", "origin", "destination", "date",
            "departure_time", "arrival_time", "duration_minutes",
            "stops", "price_usd", "passengers", "seats_available",
        }
        for f in flights:
            assert required.issubset(f.keys()), f"Missing fields in {f}"

    def test_origin_destination_uppercased(self):
        flights = _generate_flights("jfk", "lax", "2025-06-15", 1)
        for f in flights:
            assert f["origin"] == "JFK"
            assert f["destination"] == "LAX"

    def test_passengers_stored(self):
        flights = _generate_flights("JFK", "LAX", "2025-06-15", 2)
        for f in flights:
            assert f["passengers"] == 2

    def test_deterministic_for_same_inputs(self):
        a = _generate_flights("JFK", "LAX", "2025-06-15", 1)
        b = _generate_flights("JFK", "LAX", "2025-06-15", 1)
        assert [f["flight_id"] for f in a] == [f["flight_id"] for f in b]

    def test_different_routes_differ(self):
        a = _generate_flights("JFK", "LAX", "2025-06-15", 1)
        b = _generate_flights("JFK", "ORD", "2025-06-15", 1)
        assert a[0]["flight_id"] != b[0]["flight_id"]

    def test_flights_added_to_db(self):
        FLIGHT_DB.clear()
        flights = _generate_flights("BOS", "MIA", "2025-07-01", 1)
        for f in flights:
            assert f["flight_id"] in FLIGHT_DB


# ---------------------------------------------------------------------------
# call_tool – search_flights
# ---------------------------------------------------------------------------

class TestSearchFlights:
    def test_search_returns_results(self):
        FLIGHT_DB.clear()
        result = run_async(call_tool("search_flights", {
            "origin": "JFK", "destination": "LAX", "date": "2025-06-15"
        }))
        data = json.loads(result[0].text)
        assert "search_results" in data
        assert data["search_results"]["flights_found"] >= 2

    def test_search_defaults_to_one_passenger(self):
        FLIGHT_DB.clear()
        result = run_async(call_tool("search_flights", {
            "origin": "JFK", "destination": "LAX", "date": "2025-06-15"
        }))
        data = json.loads(result[0].text)
        assert data["search_results"]["passengers"] == 1

    def test_search_respects_passengers(self):
        FLIGHT_DB.clear()
        result = run_async(call_tool("search_flights", {
            "origin": "JFK", "destination": "LAX", "date": "2025-06-15", "passengers": 3
        }))
        data = json.loads(result[0].text)
        assert data["search_results"]["passengers"] == 3

    def test_invalid_date_returns_error(self):
        result = run_async(call_tool("search_flights", {
            "origin": "JFK", "destination": "LAX", "date": "not-a-date"
        }))
        data = json.loads(result[0].text)
        assert "error" in data


# ---------------------------------------------------------------------------
# call_tool – get_flight_details
# ---------------------------------------------------------------------------

class TestGetFlightDetails:
    def setup_method(self):
        FLIGHT_DB.clear()
        self.flights = _generate_flights("JFK", "LAX", "2025-06-15", 1)
        self.flight_id = self.flights[0]["flight_id"]

    def test_returns_flight(self):
        result = run_async(call_tool("get_flight_details", {"flight_id": self.flight_id}))
        data = json.loads(result[0].text)
        assert "flight" in data
        assert data["flight"]["flight_id"] == self.flight_id

    def test_unknown_flight_returns_error(self):
        result = run_async(call_tool("get_flight_details", {"flight_id": "NONEXISTENT"}))
        data = json.loads(result[0].text)
        assert "error" in data


# ---------------------------------------------------------------------------
# call_tool – book_flight
# ---------------------------------------------------------------------------

class TestBookFlight:
    def setup_method(self):
        FLIGHT_DB.clear()
        BOOKINGS.clear()
        self.flights = _generate_flights("JFK", "LAX", "2025-06-15", 1)
        # Make sure there are seats
        for f in self.flights:
            FLIGHT_DB[f["flight_id"]]["seats_available"] = 10
        self.flight_id = self.flights[0]["flight_id"]

    def test_booking_returns_confirmation(self):
        result = run_async(call_tool("book_flight", {
            "flight_id": self.flight_id,
            "passenger_name": "Alice Smith",
            "passenger_email": "alice@example.com",
        }))
        data = json.loads(result[0].text)
        assert "booking_confirmation" in data
        bc = data["booking_confirmation"]
        assert bc["status"] == "CONFIRMED"
        assert bc["passenger_name"] == "Alice Smith"
        assert bc["passenger_email"] == "alice@example.com"
        assert bc["flight_id"] == self.flight_id
        assert bc["booking_reference"].startswith("BK")

    def test_booking_stored_in_bookings(self):
        result = run_async(call_tool("book_flight", {
            "flight_id": self.flight_id,
            "passenger_name": "Bob Jones",
            "passenger_email": "bob@example.com",
        }))
        data = json.loads(result[0].text)
        ref = data["booking_confirmation"]["booking_reference"]
        assert ref in BOOKINGS

    def test_booking_decrements_seats(self):
        seats_before = FLIGHT_DB[self.flight_id]["seats_available"]
        run_async(call_tool("book_flight", {
            "flight_id": self.flight_id,
            "passenger_name": "Carol White",
            "passenger_email": "carol@example.com",
        }))
        seats_after = FLIGHT_DB[self.flight_id]["seats_available"]
        assert seats_after == seats_before - 1

    def test_booking_unknown_flight_returns_error(self):
        result = run_async(call_tool("book_flight", {
            "flight_id": "NONEXISTENT",
            "passenger_name": "Dave Black",
            "passenger_email": "dave@example.com",
        }))
        data = json.loads(result[0].text)
        assert "error" in data

    def test_booking_no_seats_returns_error(self):
        FLIGHT_DB[self.flight_id]["seats_available"] = 0
        result = run_async(call_tool("book_flight", {
            "flight_id": self.flight_id,
            "passenger_name": "Eve Green",
            "passenger_email": "eve@example.com",
        }))
        data = json.loads(result[0].text)
        assert "error" in data


# ---------------------------------------------------------------------------
# call_tool – unknown tool
# ---------------------------------------------------------------------------

class TestUnknownTool:
    def test_unknown_tool_returns_error(self):
        result = run_async(call_tool("nonexistent_tool", {}))
        data = json.loads(result[0].text)
        assert "error" in data


# ---------------------------------------------------------------------------
# mcp_tool_to_anthropic
# ---------------------------------------------------------------------------

class TestMcpToolToAnthropic:
    def test_conversion_structure(self):
        from mcp.types import Tool

        mcp_tool = Tool(
            name="search_flights",
            description="Search for flights",
            inputSchema={
                "type": "object",
                "properties": {"origin": {"type": "string"}},
                "required": ["origin"],
            },
        )
        anthropic_tool = mcp_tool_to_anthropic(mcp_tool)
        assert anthropic_tool["name"] == "search_flights"
        assert anthropic_tool["description"] == "Search for flights"
        assert "input_schema" in anthropic_tool
        assert anthropic_tool["input_schema"]["type"] == "object"

    def test_none_description_becomes_empty_string(self):
        from mcp.types import Tool

        mcp_tool = Tool(
            name="test_tool",
            description=None,
            inputSchema={"type": "object", "properties": {}},
        )
        anthropic_tool = mcp_tool_to_anthropic(mcp_tool)
        assert anthropic_tool["description"] == ""
