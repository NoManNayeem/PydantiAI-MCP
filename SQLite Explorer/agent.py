#!/usr/bin/env python3
import asyncio
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerHTTP

async def main():
    # (1) Point at your running MCP SSE server:
    mcp = MCPServerHTTP(url="http://localhost:9000/sse")
    
    # (2) Create the agent *without* a custom system_prompt.
    #     PydanticAI will automatically discover your tools
    #     (get_schema, query_data) and inject the proper function-calling spec.
    agent = Agent(
        model="openai:gpt-4o",
        mcp_servers=[mcp],
        system_prompt=(
        'You are a Customer Service Agent and you serve customers with their queries'
        'Understand the customer query properly and then try to help with precise answers based on the database mcp tool/server.'
    ),
    )

    print("Connecting to MCP server…")
    async with agent.run_mcp_servers():
        print("✅ Connected! Start chatting. (Type /exit or blank to quit.)\n")

        while True:
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                return

            if not user_input or user_input.lower() in ("/exit", "exit"):
                print("Goodbye!")
                return

            # (3) Send it off to the agent. If the model decides to call
            #     your SQLite tools, PydanticAI will dispatch them under the hood.
            result = await agent.run(user_input)
            print("Bot:", result.output)

if __name__ == "__main__":
    # Make sure you have OPENAI_API_KEY set in your environment!
    asyncio.run(main())
