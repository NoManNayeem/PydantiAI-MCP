#!/usr/bin/env python3
import os
import sys
import sqlite3
import logging
from contextlib import closing
from pathlib import Path
from typing import Any, List, Dict

from pydantic import AnyUrl
import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Route, Mount
import uvicorn

# ensure UTF-8 I/O on Windows
if sys.platform == "win32" and os.environ.get("PYTHONIOENCODING") is None:
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_sqlite_server")
logger.info("Starting MCP SQLite Server…")

DB_PATH = Path("database.db")

class SqliteDatabase:
    def __init__(self, path: Path):
        self.db_path = path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # create file if missing
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
        self.insights: List[str] = []

    def _execute_query(self, query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        logger.debug(f"Executing SQL: {query}")
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            with closing(conn.cursor()) as cur:
                if params:
                    cur.execute(query, params)
                else:
                    cur.execute(query)
                if query.strip().upper().startswith(("INSERT","UPDATE","DELETE","CREATE","DROP","ALTER")):
                    conn.commit()
                    return [{"affected_rows": cur.rowcount}]
                rows = cur.fetchall()
                return [dict(r) for r in rows]

    def synthesize_memo(self) -> str:
        if not self.insights:
            return "No business insights have been recorded yet."
        lines = "\n".join(f"- {i}" for i in self.insights)
        memo = "📊 Business Insights Memo 📊\n\nKey Insights:\n" + lines
        if len(self.insights) > 1:
            memo += f"\n\nSummary:\n{len(self.insights)} insights suggest strategic opportunities."
        return memo

# instantiate DB helper and MCP server
db = SqliteDatabase(DB_PATH)
server = Server("sqlite-mcp-demo")

# — Resources —
@server.list_resources()
async def _list_resources() -> List[types.Resource]:
    return [
        types.Resource(
            uri=AnyUrl("memo://insights"),
            name="Business Insights Memo",
            description="A running log of insights generated during analysis",
            mimeType="text/plain",
        )
    ]

@server.read_resource()
async def _read_resource(uri: AnyUrl) -> str:
    if uri.scheme != "memo" or uri.host != "insights":
        raise ValueError(f"Unknown resource: {uri}")
    return db.synthesize_memo()

# — Prompts —
PROMPT_TEMPLATE = """
You are demonstrating an SQLite MCP Server demo for topic: {topic}.
Follow the “mcp-demo” script: first explain the demo, then set up tables, pause for user choices, run queries, append insights, build a dashboard, and finish with the memo.
"""

@server.list_prompts()
async def _list_prompts() -> List[types.Prompt]:
    return [
        types.Prompt(
            name="mcp-demo",
            description="Walk through an interactive SQLite demo",
            arguments=[ types.PromptArgument(name="topic", description="Demo topic", required=True) ],
        )
    ]

@server.get_prompt()
async def _get_prompt(name: str, args: Dict[str,str] = None) -> types.GetPromptResult:
    if name != "mcp-demo" or not args or "topic" not in args:
        raise ValueError("Prompt 'mcp-demo' requires a 'topic' argument")
    prompt_text = PROMPT_TEMPLATE.format(topic=args["topic"]).strip()
    return types.GetPromptResult(
        description=f"Demo for topic: {args['topic']}",
        messages=[ types.PromptMessage(role="user", content=types.TextContent(type="text", text=prompt_text)) ],
    )

# — Tools —
@server.list_tools()
async def _list_tools() -> List[types.Tool]:
    return [
        types.Tool(
            name="create_table",
            description="Create a new table (CREATE TABLE...)",
            inputSchema={"type":"object","required":["query"],"properties":{"query":{"type":"string"}}},
        ),
        types.Tool(
            name="read_query",
            description="Run a SELECT query",
            inputSchema={"type":"object","required":["query"],"properties":{"query":{"type":"string"}}},
        ),
        types.Tool(
            name="write_query",
            description="Run an INSERT/UPDATE/DELETE",
            inputSchema={"type":"object","required":["query"],"properties":{"query":{"type":"string"}}},
        ),
        types.Tool(
            name="list_tables",
            description="List all table names",
            inputSchema={"type":"object","properties":{}},
        ),
        types.Tool(
            name="describe_table",
            description="Describe columns of a table (PRAGMA table_info)",
            inputSchema={"type":"object","required":["table_name"],"properties":{"table_name":{"type":"string"}}},
        ),
        types.Tool(
            name="append_insight",
            description="Add a business insight to the memo",
            inputSchema={"type":"object","required":["insight"],"properties":{"insight":{"type":"string"}}},
        ),
    ]

@server.call_tool()
async def _call_tool(name: str, args: Dict[str,Any] = None) -> List[types.TextContent]:
    try:
        if name == "list_tables":
            rows = db._execute_query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
            return [types.TextContent(type="text", text=str(rows))]

        if name == "describe_table":
            tbl = args.get("table_name") if args else None
            if not tbl: raise ValueError("Missing 'table_name'")
            rows = db._execute_query(f"PRAGMA table_info({tbl});")
            return [types.TextContent(type="text", text=str(rows))]

        if name == "create_table":
            q = args["query"]
            if not q.strip().upper().startswith("CREATE TABLE"):
                raise ValueError("create_table only supports CREATE TABLE")
            res = db._execute_query(q)
            return [types.TextContent(type="text", text=str(res))]

        if name == "read_query":
            q = args["query"]
            if not q.strip().upper().startswith("SELECT"):
                raise ValueError("read_query only supports SELECT")
            rows = db._execute_query(q)
            return [types.TextContent(type="text", text=str(rows))]

        if name == "write_query":
            q = args["query"]
            if q.strip().upper().startswith("SELECT"):
                raise ValueError("write_query does not support SELECT")
            res = db._execute_query(q)
            return [types.TextContent(type="text", text=str(res))]

        if name == "append_insight":
            itm = args["insight"]
            db.insights.append(itm)
            # notify clients the resource changed
            await server.request_context.session.send_resource_updated(AnyUrl("memo://insights"))
            return [types.TextContent(type="text", text="Insight appended")]

        raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        return [types.TextContent(type="text", text=f"Error: {e}")]

# — SSE transport & ASGI app —
sse = SseServerTransport("/messages/")

async def handle_sse(request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as (recv, send):
        await server.run(
            recv,
            send,
            server.create_initialization_options(),
        )

app = Starlette(
    debug=True,
    routes=[
        Route("/sse", handle_sse),
        Mount("/messages/", app=sse.handle_post_message),
    ],
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9000)
