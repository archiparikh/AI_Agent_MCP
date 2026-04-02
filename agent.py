"""
Claude AI Agent with MCP Flight Tools.

This agent uses Anthropic's Claude model to answer flight-related queries
by calling tools exposed by the flight MCP server (flight_mcp_server.py).

Usage:
    python agent.py
    python agent.py --query "Find me flights from NYC to London on 2025-06-15"
"""

import asyncio
import json
import sys
import argparse

import anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL = "claude-opus-4-5"
MAX_TOKENS = 4096
SYSTEM_PROMPT = """You are a helpful flight booking assistant. You have access to tools that let you:
1. Search for available flights between cities or airports
2. Retrieve detailed information about specific flights
3. Book flights for passengers

When helping users:
- Always search for flights before attempting to book
- Present flight options clearly with prices, times, and stops
- Confirm all details with the user before booking (unless they've explicitly asked you to proceed)
- Provide booking confirmation details after a successful booking
- Use today's date context when the user says things like "tomorrow" or "next week"

Be friendly, concise, and helpful."""


# ---------------------------------------------------------------------------
# MCP tool → Anthropic tool format conversion
# ---------------------------------------------------------------------------

def mcp_tool_to_anthropic(mcp_tool) -> dict:
    """Convert an MCP Tool object to the Anthropic tool dict format."""
    return {
        "name": mcp_tool.name,
        "description": mcp_tool.description or "",
        "input_schema": mcp_tool.inputSchema,
    }


# ---------------------------------------------------------------------------
# Agentic loop
# ---------------------------------------------------------------------------

async def run_agent(session: ClientSession, query: str, verbose: bool = True) -> str:
    """
    Run the Claude agentic loop for a given user query.

    The loop continues until Claude returns a stop_reason of 'end_turn'
    (i.e., no more tool calls are needed).
    """
    client = anthropic.Anthropic()

    # Fetch available tools from MCP server
    tools_response = await session.list_tools()
    tools = [mcp_tool_to_anthropic(t) for t in tools_response.tools]

    messages = [{"role": "user", "content": query}]

    if verbose:
        print(f"\n{'='*60}")
        print(f"User: {query}")
        print(f"{'='*60}")

    final_text = ""

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )

        # Collect text and tool_use blocks from the response
        assistant_content = []
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                assistant_content.append({"type": "text", "text": block.text})
                if block.text:
                    final_text = block.text
                    if verbose:
                        print(f"\nAssistant: {block.text}")
            elif block.type == "tool_use":
                assistant_content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })
                tool_calls.append(block)

        # Add assistant message to conversation history
        messages.append({"role": "assistant", "content": assistant_content})

        # If no tool calls, we're done
        if response.stop_reason == "end_turn" or not tool_calls:
            break

        # Execute tool calls via MCP and collect results
        tool_results = []
        for tool_call in tool_calls:
            if verbose:
                print(f"\n[Tool Call] {tool_call.name}({json.dumps(tool_call.input, indent=2)})")

            result = await session.call_tool(tool_call.name, tool_call.input)

            result_text = ""
            for content_item in result.content:
                if hasattr(content_item, "text"):
                    result_text += content_item.text

            if verbose:
                print(f"[Tool Result] {result_text[:500]}{'...' if len(result_text) > 500 else ''}")

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_call.id,
                "content": result_text,
            })

        # Add tool results to conversation as a user message
        messages.append({"role": "user", "content": tool_results})

    return final_text


# ---------------------------------------------------------------------------
# Interactive REPL
# ---------------------------------------------------------------------------

async def interactive_loop(session: ClientSession):
    """Run an interactive multi-turn conversation with the agent."""
    print("\n✈️  Flight Booking Agent (powered by Claude + MCP)")
    print("Type your flight query below. Type 'quit' or 'exit' to stop.\n")

    while True:
        try:
            query = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not query:
            continue
        if query.lower() in {"quit", "exit", "q"}:
            print("Goodbye!")
            break

        try:
            await run_agent(session, query)
        except anthropic.APIError as exc:
            print(f"[API Error] {exc}")
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as exc:
            print(f"[Error] {type(exc).__name__}: {exc}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    parser = argparse.ArgumentParser(description="Claude + MCP Flight Booking Agent")
    parser.add_argument(
        "--query",
        type=str,
        default=None,
        help="Run a single query instead of the interactive REPL",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress tool call logs (only show final answer)",
    )
    args = parser.parse_args()

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["flight_mcp_server.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            if args.query:
                await run_agent(session, args.query, verbose=not args.quiet)
            else:
                await interactive_loop(session)


if __name__ == "__main__":
    asyncio.run(main())
