#!/usr/bin/env python3
import asyncio
import sys
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerHTTP

async def main():
    # (1) Point at your running MCP SSE server:
    mcp = MCPServerHTTP(url="http://localhost:9000/sse")
    
    # (2) Create the agent *without* a custom system_prompt.
    #     PydanticAI will automatically pull your two tools (weather, add)
    #     and inject the correct function-calling instructions into the LLM.
    agent = Agent(
        model="openai:gpt-4o",
        mcp_servers=[mcp],
    )

    print("Connecting to MCP server…")
    async with agent.run_mcp_servers():  # establishes the HTTP+SSE streams :contentReference[oaicite:0]{index=0}
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
            #     your weather/add tools, PydanticAI will detect the RPC
            #     and dispatch to your server under the hood.
            result = await agent.run(user_input)
            print("Bot:", result.output)

if __name__ == "__main__":
    asyncio.run(main())
