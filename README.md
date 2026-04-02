# AI Agent – MongoDB MCP Integration

An AI agent that integrates with the [MongoDB MCP server](https://www.npmjs.com/package/mongodb-mcp-server) to answer natural-language queries about a local MongoDB flight-booking database, powered by Claude (Anthropic).

---

## How it works

```
User query
    │
    ▼
Claude (claude-3-5-sonnet)  ◄──────────────────┐
    │  tool_use request                         │
    ▼                                           │
MongoDB MCP Server (stdio)                      │
    │  runs queries against                     │
    ▼                                           │
Local MongoDB (ai_agent_db)                     │
    │  returns results                          │
    └──────────────────────────────────────────►┘
```

The MCP server exposes MongoDB operations (find, aggregate, insert, update, etc.) as tools. The agent passes those tool definitions to Claude, which decides which queries to run, calls the tools, and formulates a final answer.

---

## Project structure

```
.
├── src/
│   ├── agent.js   – AI agent (agentic loop with tool use)
│   ├── seed.js    – Seed the local MongoDB with sample data
│   └── test.js    – Integration tests
├── mcp_config.json            – MCP server configuration reference
├── .github/workflows/
│   └── mongodb-mcp.yml        – CI: spin up MongoDB, seed, test
└── package.json
```
# AI_Agent_MCP

A **Claude-powered AI Agent** that integrates with the **Model Context Protocol (MCP)** to search for flights and book them through a conversational interface.

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  agent.py                        │
│  ┌───────────────────────────────────────────┐  │
│  │  Claude (claude-opus-4-5)                 │  │
│  │  Agentic loop with tool_use               │  │
│  └──────────────────┬────────────────────────┘  │
│                     │  MCP (stdio transport)     │
│  ┌──────────────────▼────────────────────────┐  │
│  │  flight_mcp_server.py                     │  │
│  │  ├── search_flights                       │  │
│  │  ├── get_flight_details                   │  │
│  │  └── book_flight                          │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

### Components

| File | Description |
|---|---|
| `flight_mcp_server.py` | MCP server exposing flight search & booking tools |
| `agent.py` | Claude agent that drives the conversation and calls MCP tools |
| `requirements.txt` | Python dependencies |
| `tests/test_flight_agent.py` | Unit tests for the server tools and agent utilities |

---

## Prerequisites

| Tool | Version |
|------|---------|
| Node.js | ≥ 18 |
| MongoDB | ≥ 6 (local) |
| Anthropic API key | — |

---

## Quick start

### 1. Install dependencies

```bash
npm install
```

### 2. Start a local MongoDB instance

```bash
# Using Docker
docker run -d -p 27017:27017 --name mongo mongo:7

# Or start your local mongod
mongod --dbpath /data/db
```

### 3. Seed the database

```bash
MONGODB_URI=mongodb://localhost:27017 npm run seed
```

### 4. Run the agent

```bash
ANTHROPIC_API_KEY=<your-key> MONGODB_URI=mongodb://localhost:27017 npm start
- Python 3.11+
- An Anthropic API key ([get one here](https://console.anthropic.com/))

---

## Setup

```bash
# 1. Clone the repository
git clone https://github.com/archiparikh/AI_Agent_MCP.git
cd AI_Agent_MCP

# 2. (Optional) create a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Export your Anthropic API key
export ANTHROPIC_API_KEY="sk-ant-..."
```

---

## Usage

### Interactive REPL

Start a conversation with the agent:

```bash
python agent.py
```

Example session:

```
You: Which flights have fewer than 20 seats available?
[Tool] find({"collection":"flights","filter":{"availableSeats":{"$lt":20}}})

Two flights have fewer than 20 available seats:
• AI303 Paris → Tokyo  – 12 seats  – $1,200
• AI505 Sydney → New York – 5 seats  – $1,500
```

### 5. Run integration tests

```bash
MONGODB_URI=mongodb://localhost:27017 npm test
```

---

## MCP server configuration (`mcp_config.json`)

This file can be used directly with MCP-compatible clients (e.g. Claude Desktop, Cursor):

```json
{
  "mcpServers": {
    "mongodb": {
      "command": "npx",
      "args": ["-y", "mongodb-mcp-server"],
      "env": {
        "MDB_MCP_CONNECTION_STRING": "mongodb://localhost:27017"
      }
    }
  }
}
```

---

## GitHub Actions CI

The workflow at `.github/workflows/mongodb-mcp.yml` automatically:

1. Spins up a MongoDB 7 service container.
2. Installs dependencies (`npm ci`).
3. Seeds the database (`npm run seed`).
4. Runs the integration tests (`npm test`).

Set `ANTHROPIC_API_KEY` as a [GitHub Actions secret](https://docs.github.com/en/actions/security-guides/encrypted-secrets) if you add agent-level tests that call the Anthropic API.
✈️  Flight Booking Agent (powered by Claude + MCP)
Type your flight query below. Type 'quit' or 'exit' to stop.

You: Find me flights from New York to London on 2025-08-10
...
You: Book the cheapest one for John Doe, john@example.com
...
You: quit
```

### Single query (non-interactive)

```bash
python agent.py --query "Search for 2 flights from JFK to CDG on 2025-09-01"
```

Add `--quiet` to suppress tool-call logs and only show the final answer:

```bash
python agent.py --query "Find flights from BOS to MIA on 2025-07-04" --quiet
```

---

## MCP Tools

### `search_flights`
Search for available flights between two airports/cities.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `origin` | string | ✅ | Origin airport code or city (e.g. `JFK`) |
| `destination` | string | ✅ | Destination airport code or city (e.g. `LAX`) |
| `date` | string | ✅ | Travel date (`YYYY-MM-DD`) |
| `passengers` | integer | ➖ | Number of passengers (default: `1`) |

### `get_flight_details`
Retrieve detailed information about a specific flight.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `flight_id` | string | ✅ | Flight ID returned by `search_flights` |

### `book_flight`
Book a flight and receive a confirmation reference.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `flight_id` | string | ✅ | Flight ID to book |
| `passenger_name` | string | ✅ | Full name of the primary passenger |
| `passenger_email` | string | ✅ | Email address of the primary passenger |

---

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

---

## How It Works

1. **`agent.py`** spawns `flight_mcp_server.py` as a subprocess and connects to it via MCP's stdio transport.
2. It calls `session.list_tools()` to discover the available flight tools and converts them to the Anthropic tool-use format.
3. The user's message is sent to **Claude** along with the tool definitions.
4. Claude decides which tool(s) to call; the agent executes them via MCP and feeds the results back to Claude.
5. The loop repeats until Claude produces a final answer (`stop_reason == "end_turn"`).
