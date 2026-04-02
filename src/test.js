"use strict";

/**
 * test.js – Integration tests for the MongoDB MCP server connection
 * and the local database schema.
 *
 * Requires a running MongoDB instance at MONGODB_URI (default: localhost:27017).
 * Run `npm run seed` first to populate the database.
 */

const { MongoClient } = require("mongodb");

const MONGODB_URI = process.env.MONGODB_URI || "mongodb://localhost:27017";
const DB_NAME = "ai_agent_db";

let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (condition) {
    console.log(`  ✓ ${message}`);
    passed++;
  } else {
    console.error(`  ✗ ${message}`);
    failed++;
  }
}

async function run() {
  const client = new MongoClient(MONGODB_URI);
  try {
    await client.connect();
    const db = client.db(DB_NAME);

    // -----------------------------------------------------------------------
    console.log("\nTest: flights collection");
    // -----------------------------------------------------------------------
    const flightCount = await db.collection("flights").countDocuments();
    assert(flightCount > 0, `flights collection has ${flightCount} document(s)`);

    const flight = await db.collection("flights").findOne({ flightNumber: "AI101" });
    assert(flight !== null, "flight AI101 exists");
    assert(typeof flight.price === "number", "flight price is a number");
    assert(typeof flight.availableSeats === "number", "availableSeats is a number");

    // -----------------------------------------------------------------------
    console.log("\nTest: bookings collection");
    // -----------------------------------------------------------------------
    const bookingCount = await db.collection("bookings").countDocuments();
    assert(bookingCount > 0, `bookings collection has ${bookingCount} document(s)`);

    const booking = await db.collection("bookings").findOne({ bookingRef: "BK001" });
    assert(booking !== null, "booking BK001 exists");
    assert(booking.status === "confirmed", "booking BK001 is confirmed");

    // -----------------------------------------------------------------------
    console.log("\nTest: query – available flights with seats");
    // -----------------------------------------------------------------------
    const available = await db
      .collection("flights")
      .find({ availableSeats: { $gt: 0 } })
      .toArray();
    assert(available.length > 0, `${available.length} flight(s) have available seats`);

    // -----------------------------------------------------------------------
    console.log("\nTest: query – flights sorted by price");
    // -----------------------------------------------------------------------
    const sorted = await db
      .collection("flights")
      .find({})
      .sort({ price: 1 })
      .toArray();
    assert(
      sorted[0].price <= sorted[sorted.length - 1].price,
      "flights are sorted cheapest-first"
    );
  } finally {
    await client.close();
  }

  console.log(`\n${passed} passed, ${failed} failed.\n`);
  if (failed > 0) process.exit(1);
}

run().catch((err) => {
  console.error("Test run failed:", err);
  process.exit(1);
});
