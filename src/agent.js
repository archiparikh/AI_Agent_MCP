"use strict";

/**
 * agent.js – AI Agent that uses the MongoDB MCP server to answer
 * flight-related queries against a local MongoDB database.
 *
 * The agent:
 *  1. Spawns the MongoDB MCP server as a child process.
 *  2. Communicates with it over stdio using the MCP JSON-RPC protocol.
 *  3. Exposes the server's tools to Claude (Anthropic) via tool_use.
 *  4. Runs an interactive loop answering user queries.
 *
 * Environment variables:
 *   ANTHROPIC_API_KEY  – required
 *   MONGODB_URI        – defaults to mongodb://localhost:27017
 */

const { spawn } = require("child_process");
const readline = require("readline");
const Anthropic = require("@anthropic-ai/sdk");

const MONGODB_URI = process.env.MONGODB_URI || "mongodb://localhost:27017";
const MODEL = "claude-3-5-sonnet-20241022";

// ---------------------------------------------------------------------------
// Minimal MCP stdio client
// ---------------------------------------------------------------------------

class McpClient {
  constructor(command, args, env) {
    this._nextId = 1;
    this._pending = new Map();
    this._tools = [];

    this._proc = spawn(command, args, {
      env: { ...process.env, ...env },
      stdio: ["pipe", "pipe", "inherit"],
    });

    this._proc.on("error", (err) => {
      console.error("[MCP] process error:", err.message);
    });

    // Buffer incoming data and split on newlines
    let buffer = "";
    this._proc.stdout.on("data", (chunk) => {
      buffer += chunk.toString();
      const lines = buffer.split("\n");
      buffer = lines.pop(); // keep incomplete last line
      for (const line of lines) {
        if (line.trim()) this._handleMessage(line.trim());
      }
    });
  }

  _handleMessage(raw) {
    let msg;
    try {
      msg = JSON.parse(raw);
    } catch {
      return; // ignore non-JSON lines
    }

    if (msg.id !== undefined && this._pending.has(msg.id)) {
      const { resolve, reject } = this._pending.get(msg.id);
      this._pending.delete(msg.id);
      if (msg.error) reject(new Error(msg.error.message));
      else resolve(msg.result);
    }
  }

  _send(method, params) {
    return new Promise((resolve, reject) => {
      const id = this._nextId++;
      this._pending.set(id, { resolve, reject });
      const msg = JSON.stringify({ jsonrpc: "2.0", id, method, params });
      this._proc.stdin.write(msg + "\n");
    });
  }

  async initialize() {
    await this._send("initialize", {
      protocolVersion: "2024-11-05",
      capabilities: {},
      clientInfo: { name: "ai-agent", version: "1.0.0" },
    });
    // Send initialized notification
    this._proc.stdin.write(
      JSON.stringify({ jsonrpc: "2.0", method: "notifications/initialized" }) + "\n"
    );
  }

  async listTools() {
    const result = await this._send("tools/list", {});
    this._tools = result.tools || [];
    return this._tools;
  }

  async callTool(name, args) {
    const result = await this._send("tools/call", {
      name,
      arguments: args,
    });
    return result;
  }

  get tools() {
    return this._tools;
  }

  close() {
    this._proc.stdin.end();
    this._proc.kill();
  }
}

// ---------------------------------------------------------------------------
// Convert MCP tool definitions to Anthropic tool format
// ---------------------------------------------------------------------------

function toAnthropicTools(mcpTools) {
  return mcpTools.map((t) => ({
    name: t.name,
    description: t.description || "",
    input_schema: t.inputSchema || { type: "object", properties: {} },
  }));
}

// ---------------------------------------------------------------------------
// Agentic loop
// ---------------------------------------------------------------------------

async function runAgent(mcp, anthropic, userMessage) {
  console.log("\nUser:", userMessage);

  const anthropicTools = toAnthropicTools(mcp.tools);
  const messages = [{ role: "user", content: userMessage }];

  const systemPrompt =
    "You are a helpful flight booking assistant. " +
    "You have access to a MongoDB database containing flights and bookings collections. " +
    "Use the provided tools to answer questions about available flights, " +
    "seat availability, prices, and existing bookings. " +
    "Always present prices with their currency symbol.";

  // Agentic loop: keep calling Claude until it stops requesting tool use
  while (true) {
    const response = await anthropic.messages.create({
      model: MODEL,
      max_tokens: 1024,
      system: systemPrompt,
      tools: anthropicTools,
      messages,
    });

    // Collect text and tool use blocks
    const toolUseBlocks = response.content.filter((b) => b.type === "tool_use");
    const textBlocks = response.content.filter((b) => b.type === "text");

    if (textBlocks.length > 0) {
      for (const tb of textBlocks) process.stdout.write(tb.text);
    }

    if (response.stop_reason !== "tool_use" || toolUseBlocks.length === 0) {
      console.log("\n");
      break;
    }

    // Execute all requested tool calls
    messages.push({ role: "assistant", content: response.content });

    const toolResults = [];
    for (const tu of toolUseBlocks) {
      console.log(`\n[Tool] ${tu.name}(${JSON.stringify(tu.input)})`);
      try {
        const result = await mcp.callTool(tu.name, tu.input);
        const resultText =
          result.content
            ?.map((c) => (c.type === "text" ? c.text : JSON.stringify(c)))
            .join("\n") || JSON.stringify(result);

        toolResults.push({
          type: "tool_result",
          tool_use_id: tu.id,
          content: resultText,
        });
      } catch (err) {
        toolResults.push({
          type: "tool_result",
          tool_use_id: tu.id,
          is_error: true,
          content: err.message,
        });
      }
    }

    messages.push({ role: "user", content: toolResults });
  }
}

// ---------------------------------------------------------------------------
// Main entry point
// ---------------------------------------------------------------------------

async function main() {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    console.error("Error: ANTHROPIC_API_KEY environment variable is required.");
    process.exit(1);
  }

  const anthropic = new Anthropic({ apiKey });

  console.log("Starting MongoDB MCP server…");
  const mcp = new McpClient(
    "npx",
    ["-y", "mongodb-mcp-server", "--connectionString", MONGODB_URI],
    {}
  );

  try {
    await mcp.initialize();
    const tools = await mcp.listTools();
    console.log(`MCP server ready – ${tools.length} tool(s) available.\n`);

    // Interactive readline loop
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
      terminal: false,
    });

    const prompt = () => process.stdout.write("You: ");
    prompt();

    for await (const line of rl) {
      const query = line.trim();
      if (!query) {
        prompt();
        continue;
      }
      if (query.toLowerCase() === "exit") break;

      await runAgent(mcp, anthropic, query);
      prompt();
    }
  } finally {
    mcp.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
