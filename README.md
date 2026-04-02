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
