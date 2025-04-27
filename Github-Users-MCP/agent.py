#!/usr/bin/env python3
import asyncio
import sys
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerHTTP

async def main():
    # Point at your MCP server's SSE endpoint
    server = MCPServerHTTP(url="http://localhost:9000/sse")

    # Create the agent; it will auto-discover the 'github_search' tool
    agent = Agent(
        model="openai:gpt-4o",
        mcp_servers=[server],
    )

    print("Connecting to MCP server…")
    async with agent.run_mcp_servers():
        print("✅ Connected! Start chatting. (Type /exit to quit.)\n")
        try:
            while True:
                user_input = input("You: ").strip()
                if not user_input or user_input.lower() in ("/exit", "exit"):
                    print("Goodbye!")
                    return

                # Send the query to the agent; it will call github_search() when appropriate
                result = await agent.run(user_input)
                print("Bot:", result.output)
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
