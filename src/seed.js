"use strict";

/**
 * seed.js – Populate the local MongoDB database with sample data.
 *
 * Usage:
 *   MONGODB_URI=mongodb://localhost:27017 node src/seed.js
 */

const { MongoClient } = require("mongodb");

const MONGODB_URI = process.env.MONGODB_URI || "mongodb://localhost:27017";
const DB_NAME = "ai_agent_db";

const flights = [
  {
    flightNumber: "AI101",
    origin: "New York",
    destination: "London",
    departureTime: new Date("2026-05-01T08:00:00Z"),
    arrivalTime: new Date("2026-05-01T20:00:00Z"),
    seats: 180,
    availableSeats: 45,
    price: 650,
    currency: "USD",
  },
  {
    flightNumber: "AI202",
    origin: "London",
    destination: "Paris",
    departureTime: new Date("2026-05-02T10:30:00Z"),
    arrivalTime: new Date("2026-05-02T12:00:00Z"),
    seats: 120,
    availableSeats: 80,
    price: 110,
    currency: "EUR",
  },
  {
    flightNumber: "AI303",
    origin: "Paris",
    destination: "Tokyo",
    departureTime: new Date("2026-05-03T14:00:00Z"),
    arrivalTime: new Date("2026-05-04T09:00:00Z"),
    seats: 250,
    availableSeats: 12,
    price: 1200,
    currency: "USD",
  },
  {
    flightNumber: "AI404",
    origin: "Tokyo",
    destination: "Sydney",
    departureTime: new Date("2026-05-05T06:00:00Z"),
    arrivalTime: new Date("2026-05-05T19:00:00Z"),
    seats: 200,
    availableSeats: 98,
    price: 900,
    currency: "USD",
  },
  {
    flightNumber: "AI505",
    origin: "Sydney",
    destination: "New York",
    departureTime: new Date("2026-05-07T22:00:00Z"),
    arrivalTime: new Date("2026-05-08T18:00:00Z"),
    seats: 350,
    availableSeats: 5,
    price: 1500,
    currency: "USD",
  },
];

const bookings = [
  {
    bookingRef: "BK001",
    flightNumber: "AI101",
    passengerName: "Alice Johnson",
    passengerEmail: "alice@example.com",
    seatNumber: "12A",
    status: "confirmed",
    createdAt: new Date(),
  },
  {
    bookingRef: "BK002",
    flightNumber: "AI202",
    passengerName: "Bob Smith",
    passengerEmail: "bob@example.com",
    seatNumber: "7C",
    status: "confirmed",
    createdAt: new Date(),
  },
];

async function seed() {
  const client = new MongoClient(MONGODB_URI);
  try {
    await client.connect();
    console.log("Connected to MongoDB:", MONGODB_URI);

    const db = client.db(DB_NAME);

    // Drop and re-create collections for a clean seed
    await db.collection("flights").drop().catch(() => {});
    await db.collection("bookings").drop().catch(() => {});

    const flightResult = await db.collection("flights").insertMany(flights);
    console.log(`Inserted ${flightResult.insertedCount} flights.`);

    const bookingResult = await db.collection("bookings").insertMany(bookings);
    console.log(`Inserted ${bookingResult.insertedCount} bookings.`);

    console.log("Database seeded successfully.");
  } finally {
    await client.close();
  }
}

seed().catch((err) => {
  console.error("Seed failed:", err);
  process.exit(1);
});
