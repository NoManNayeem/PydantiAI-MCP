# server.py

import httpx
import pandas as pd
from datetime import datetime
import uvicorn
import xml.etree.ElementTree as ET
from starlette.applications import Starlette
from starlette.routing import Mount

from mcp.server.fastmcp import FastMCP

# --- Sample DataFrame for pandas_cmd ---
df = pd.DataFrame({
    "name":  ["Alice", "Bob", "Charlie", "Diana"],
    "age":   [25, 30, 35, 40],
    "score": [85, 92, 78, 90],
})

# --- Create the MCP server ---
mcp = FastMCP("example-server")


# --- 1) weather tool ---
@mcp.tool()
async def weather(location: str) -> str:
    """Get current weather for a city via Open-Meteo."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        geo = await client.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": location, "count": 1},
        )
        results = geo.json().get("results") or []
        if not results:
            return f"❌ Location not found: {location}"
        lat, lon = results[0]["latitude"], results[0]["longitude"]

        resp = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": lat, "longitude": lon, "current_weather": True},
        )
        cw = resp.json().get("current_weather", {})
        return (
            f"🌤 Current weather in {location} "
            f"({lat:.2f}, {lon:.2f}): "
            f"{cw.get('temperature')}°C, "
            f"wind {cw.get('windspeed')} m/s "
            f"(code {cw.get('weathercode')})"
        )


# --- 2) add tool ---
@mcp.tool()
def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b


# --- 3) current_datetime tool ---
@mcp.tool()
def current_datetime() -> str:
    """Return the current local date and time as ISO-8601."""
    return datetime.now().isoformat()


# --- 4) duckduckgo_search tool ---
@mcp.tool()
async def duckduckgo_search(query: str) -> str:
    """Instant Answer via DuckDuckGo JSON API."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            "https://api.duckduckgo.com/",
            params={
                "q": query,
                "format": "json",
                "no_html": 1,
                "skip_disambig": 1,
            },
        )
    data = resp.json()
    if text := data.get("AbstractText"):
        url = data.get("AbstractURL", "")
        return f"{text} ({url})" if url else text

    for topic in data.get("RelatedTopics", []):
        if text := topic.get("Text"):
            url = topic.get("FirstURL", "")
            return f"{text} ({url})" if url else text
        for sub in topic.get("Topics", []):
            if text := sub.get("Text"):
                url = sub.get("FirstURL", "")
                return f"{text} ({url})" if url else text

    return "No results found."


# --- 5) latest_news tool (RSS parsing) ---
@mcp.tool()
async def latest_news(count: int = 5) -> str:
    """
    Fetch the top `count` headlines from CNN’s RSS feed.
    Parses the XML directly to avoid external dependencies.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get("http://rss.cnn.com/rss/edition.rss")
    root = ET.fromstring(resp.content)
    items = root.findall("./channel/item")[:count]

    lines = []
    for i, item in enumerate(items, start=1):
        title = item.findtext("title")
        link  = item.findtext("link")
        lines.append(f"{i}. {title} — {link}")
    return "\n".join(lines)


# --- 6) pandas_cmd tool (generic DataFrame execution) ---
@mcp.tool()
def pandas_cmd(cmd: str) -> str:
    """
    Execute any pandas expression on the in-memory DataFrame `df`.
    Examples:
      •   head(5)
      •   describe()
      •   query('age > 30')
      •   sort_values('score', ascending=False)
    Returns JSON for DataFrame/Series, or string otherwise.
    """
    try:
        result = eval(f"df.{cmd}", {"df": df, "pd": pd})
        if isinstance(result, (pd.DataFrame, pd.Series)):
            return result.to_json(orient="records")
        return str(result)
    except Exception as e:
        return f"Error executing pandas command: {e}"


# --- Mount the HTTP+SSE app at “/” and run on port 9000 ---
app = Starlette(routes=[Mount("/", app=mcp.sse_app())])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9000)
