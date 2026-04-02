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
