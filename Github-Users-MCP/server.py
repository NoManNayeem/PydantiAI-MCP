# server.py

import os
import json
import httpx
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Mount

from mcp.server.fastmcp import FastMCP

# 1) Instantiate FastMCP
mcp = FastMCP("example-server")

# 2) github_search tool: search public GitHub users by name and/or location
@mcp.tool()
async def github_search(
    name: str | None = None,
    location: str | None = None,
    per_page: int = 5
) -> str:
    """
    Search GitHub users by login (name) and/or location.
    - name: full or partial username
    - location: city, country, etc.
    - per_page: number of results to return (default 5)
    """
    q_parts = []
    if name:
        q_parts.append(f"{name} in:login")
    if location:
        q_parts.append(f"location:{location}")
    if not q_parts:
        return json.dumps({"error": "Provide at least one of 'name' or 'location'."})

    query = "+".join(q_parts)
    headers = {"Accept": "application/vnd.github.v3+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            "https://api.github.com/search/users",
            params={"q": query, "per_page": per_page},
            headers=headers,
        )

    if resp.status_code != 200:
        return json.dumps({
            "error": f"GitHub API returned {resp.status_code}: {resp.text}"
        })

    items = resp.json().get("items", [])
    results = [
        {"login": u["login"], "url": u["html_url"], "score": u.get("score", 0)}
        for u in items
    ]
    return json.dumps(results)

# 3) Mount the MCP SSE/JSON-RPC ASGI app at root
app = Starlette(
    routes=[
        Mount("/", app=mcp.sse_app()),  # provides "/sse" & "/messages"
    ]
)

if __name__ == "__main__":
    # 4) Run with Uvicorn on 0.0.0.0:9000
    uvicorn.run(app, host="0.0.0.0", port=9000)
