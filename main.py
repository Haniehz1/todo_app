

"""
To-Do MCP Server for mcp-agent Cloud
-------------------------------------
MCP server for todo list management, compatible with OpenAI Apps SDK.
Deployable to mcp-agent cloud.

Deploy with:
  uv run mcp-agent login
  uv run mcp-agent deploy --no-auth

Tools:
- get_tasks() - Returns all todo items
- add_task(text, due_date?) - Adds a new task
- mark_done(task_id, done?) - Marks task as complete/incomplete
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import uuid
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional

import mcp.types as types
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel
from mcp_agent.app import MCPApp

# ------------------------------
# Configuration
# ------------------------------
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DATA_FILE = os.path.join(DATA_DIR, "tasks.json")

os.makedirs(DATA_DIR, exist_ok=True)
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"tasks": []}, f)

# ------------------------------
# Models
# ------------------------------
class Task(BaseModel):
    id: str
    text: str
    done: bool = False
    created_at: str
    due_date: Optional[str] = None

class TaskList(BaseModel):
    tasks: List[Task]

# ------------------------------
# Storage helpers
# ------------------------------
def _read_store() -> TaskList:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return TaskList(tasks=[Task(**t) for t in raw.get("tasks", [])])

def _write_store(tasks: TaskList) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"tasks": [t.model_dump() for t in tasks.tasks]}, f, indent=2)

# ------------------------------
# FastMCP Server
# ------------------------------
mcp = FastMCP(
    name="todo-app",
    message_path="/sse/messages",
    stateless_http=True,
)

MIME_TYPE = "text/html+skybridge"
TEMPLATE_URI = "ui://widget/todo-list.html"
TOOL_INVOKING_TEXT = "Rendering your latest to-dos..."
TOOL_INVOKED_TEXT = "Todo list ready!"
WIDGET_ASSET_ROUTE = "/widget-assets"
WIDGET_ASSET_VERSION = os.getenv("WIDGET_ASSET_VERSION", "1")
WIDGET_DIR = Path(__file__).parent / "docs" / "widget"

BASE_WIDGET_META = {
    "openai/outputTemplate": TEMPLATE_URI,
    "openai/widgetAccessible": True,
    "openai/resultCanProduceWidget": True,
    "openai/toolInvocation/invoking": TOOL_INVOKING_TEXT,
    "openai/toolInvocation/invoked": TOOL_INVOKED_TEXT,
}

# Widget HTML
TODO_WIDGET_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="{CSS_PATH}">
</head>
<body>
    <div id="todo-root" data-widget-version="{WIDGET_VERSION}"></div>
    <script id="todo-data" type="application/json">{{TASKS_JSON}}</script>
    <script type="module">
        import {{ renderTodoWidget }} from "{JS_PATH}";
        const dataEl = document.getElementById("todo-data");
        let payload = {{ tasks: [] }};
        try {{
            payload = JSON.parse(dataEl.textContent);
        }} catch (error) {{
            console.error("todo-widget: failed to parse JSON", error);
        }}
        const root = document.getElementById("todo-root");
        renderTodoWidget({{ root, tasks: payload.tasks ?? [], postMessageTarget: window.parent }});
    </script>
</body>
</html>
"""

def _render_widget_html(tasks_data: Dict[str, Any]) -> str:
    """Render widget HTML that defers UI rendering to the hosted bundle."""
    assets_base = WIDGET_ASSET_ROUTE.rstrip("/")
    css_path = f"{assets_base}/todo.css?v={WIDGET_ASSET_VERSION}"
    js_path = f"{assets_base}/todo.js?v={WIDGET_ASSET_VERSION}"

    tasks_json = json.dumps(tasks_data).replace("</", "<\\/")

    return TODO_WIDGET_HTML.format(
        CSS_PATH=css_path,
        JS_PATH=js_path,
        WIDGET_VERSION=WIDGET_ASSET_VERSION,
    ).replace("{{TASKS_JSON}}", tasks_json)

def _tool_meta() -> Dict[str, Any]:
    return {
        **BASE_WIDGET_META,
        "annotations": {
            "destructiveHint": False,
            "openWorldHint": False,
            "readOnlyHint": True,
        },
    }

def _embedded_widget_resource(tasks_data: Dict[str, Any]) -> types.EmbeddedResource:
    return types.EmbeddedResource(
        type="resource",
        resource=types.TextResourceContents(
            uri=TEMPLATE_URI,
            mimeType=MIME_TYPE,
            text=_render_widget_html(tasks_data),
            title="Todo List",
        ),
    )

# Tool definitions
@mcp._mcp_server.list_tools()
async def _list_tools() -> List[types.Tool]:
    return [
        types.Tool(
            name="get_tasks",
            title="Get Tasks",
            description="Fetches the current list of to-do items",
            inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
            _meta=_tool_meta(),
        ),
        types.Tool(
            name="add_task",
            title="Add Task",
            description="Adds a new to-do task and returns the updated list",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The task description"},
                    "due_date": {"type": "string", "description": "Optional due date in ISO 8601 format"},
                },
                "required": ["text"],
                "additionalProperties": False,
            },
            _meta=_tool_meta(),
        ),
        types.Tool(
            name="mark_done",
            title="Mark Task Done",
            description="Marks a task as done or undone by its ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "The unique ID of the task"},
                    "done": {"type": "boolean", "description": "Whether to mark as done (true) or undone (false)"},
                },
                "required": ["task_id"],
                "additionalProperties": False,
            },
            _meta=_tool_meta(),
        ),
    ]

# Resources for widget HTML
@mcp._mcp_server.list_resources()
async def _list_resources() -> List[types.Resource]:
    return [
        types.Resource(
            name="Todo List Widget",
            title="Todo List Widget",
            uri=TEMPLATE_URI,
            description="Interactive todo list display",
            mimeType=MIME_TYPE,
            _meta=_tool_meta(),
        ),
    ]

@mcp._mcp_server.list_resource_templates()
async def _list_resource_templates() -> List[types.ResourceTemplate]:
    return [
        types.ResourceTemplate(
            name="Todo List Widget",
            title="Todo List Widget",
            uriTemplate=TEMPLATE_URI,
            description="Interactive todo list display",
            mimeType=MIME_TYPE,
            _meta=_tool_meta(),
        ),
    ]

async def _handle_read_resource(req: types.ReadResourceRequest) -> types.ServerResult:
    if str(req.params.uri) == TEMPLATE_URI:
        tasks = _read_store()
        tasks_data = {"tasks": [t.model_dump() for t in tasks.tasks]}
        return types.ServerResult(
            types.ReadResourceResult(
                contents=[
                    types.TextResourceContents(
                        uri=TEMPLATE_URI,
                        mimeType=MIME_TYPE,
                        text=_render_widget_html(tasks_data),
                        _meta=_tool_meta(),
                    )
                ]
            )
        )
    return types.ServerResult(
        types.ReadResourceResult(
            contents=[],
            _meta={"error": f"Unknown resource: {req.params.uri}"},
        )
    )

mcp._mcp_server.request_handlers[types.ReadResourceRequest] = _handle_read_resource

async def _handle_call_tool(req: types.CallToolRequest) -> types.ServerResult:
    tool_name = req.params.name
    args = req.params.arguments or {}

    # Meta is populated per-response after we know the current task state.
    def _meta_with_widget(tasks_data: Dict[str, Any]) -> Dict[str, Any]:
        widget_resource = _embedded_widget_resource(tasks_data)
        return {
            "openai.com/widget": widget_resource.model_dump(mode="json"),
            **BASE_WIDGET_META,
        }

    try:
        if tool_name == "get_tasks":
            tasks = _read_store()
            tasks_data = {"tasks": [t.model_dump() for t in tasks.tasks]}
            meta = _meta_with_widget(tasks_data)

            return types.ServerResult(
                types.CallToolResult(
                    content=[
                        types.TextContent(
                            type="text",
                            text="Here are your tasks!",
                        )
                    ],
                    structuredContent=tasks_data,
                    _meta=meta,
                )
            )

        elif tool_name == "add_task":
            text = args.get("text", "").strip()
            if not text:
                return types.ServerResult(
                    types.CallToolResult(
                        content=[types.TextContent(type="text", text="Error: Task text cannot be empty")],
                        isError=True,
                    )
                )

            tasks = _read_store()
            new_task = Task(
                id=str(uuid.uuid4()),
                text=text,
                done=False,
                created_at=datetime.utcnow().isoformat() + "Z",
                due_date=args.get("due_date"),
            )
            tasks.tasks.append(new_task)
            _write_store(tasks)

            tasks_data = {"tasks": [t.model_dump() for t in tasks.tasks]}
            meta = _meta_with_widget(tasks_data)

            return types.ServerResult(
                types.CallToolResult(
                    content=[
                        types.TextContent(
                            type="text",
                            text=f"✓ Added task: {new_task.text}",
                        )
                    ],
                    structuredContent=tasks_data,
                    _meta=meta,
                )
            )

        elif tool_name == "mark_done":
            task_id = args.get("task_id")
            done = args.get("done", True)

            tasks = _read_store()
            updated = False

            for task in tasks.tasks:
                if task.id == task_id:
                    task.done = done
                    updated = True
                    break

            if not updated:
                return types.ServerResult(
                    types.CallToolResult(
                        content=[types.TextContent(type="text", text=f"Error: Task with ID {task_id} not found")],
                        isError=True,
                    )
                )

            _write_store(tasks)

            tasks_data = {"tasks": [t.model_dump() for t in tasks.tasks]}
            meta = _meta_with_widget(tasks_data)

            return types.ServerResult(
                types.CallToolResult(
                    content=[
                        types.TextContent(
                            type="text",
                            text=f"✓ Task {'completed' if done else 'reopened'}!",
                        )
                    ],
                    structuredContent=tasks_data,
                    _meta=meta,
                )
            )

        else:
            return types.ServerResult(
                types.CallToolResult(
                    content=[types.TextContent(type="text", text=f"Unknown tool: {tool_name}")],
                    isError=True,
                )
            )

    except Exception as e:
        return types.ServerResult(
            types.CallToolResult(
                content=[types.TextContent(type="text", text=f"Error: {str(e)}")],
                isError=True,
            )
        )

mcp._mcp_server.request_handlers[types.CallToolRequest] = _handle_call_tool

# MCPApp used by mcp-agent Cloud deployments
app = MCPApp(
    name="todo-app",
    description="Todo list manager with FastMCP tools",
    mcp=mcp,
)

# ASGI app for local development
http_app = mcp.streamable_http_app()

# Add CORS to the local ASGI app
try:
    from starlette.middleware.cors import CORSMiddleware

    http_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )
except Exception:
    pass

try:
    from starlette.staticfiles import StaticFiles

    if WIDGET_DIR.exists():
        http_app.mount(
            WIDGET_ASSET_ROUTE,
            StaticFiles(directory=str(WIDGET_DIR), html=True),
            name="widget-assets",
        )
except Exception:
    pass
