# To‑Do ChatGPT App (MCP + OpenAI Apps SDK)

## Overview
This is a minimal example of a ChatGPT App built with the OpenAI **Apps SDK** and hosted via **mcp‑agent Cloud**. It demonstrates proper Model Context Protocol (MCP) integration, structured JSON tool definitions, and a compliant 1‑to‑2‑action design pattern.

## Architecture
```
ChatGPT (Apps SDK)
     │
     ▼
mcp‑agent Cloud (MCP Server)
     │
     ▼
JSON datastore (tasks.json)
```
The request–response flow works as follows: ChatGPT calls tools defined in the app. The calls are routed to the mcp‑agent Cloud, which executes the requested tool logic and returns structured_content responses back to ChatGPT.

## Endpoints (MCP Spec)
- `POST /mcp/tools/list` — Returns the list of available tool descriptors.
- `POST /mcp/tools/execute` — Executes a specific tool by name with provided arguments.

## Tools
1. **get_tasks()** — Returns the current to‑do items.  
   Input: `{}`  
   Output: `{ tasks: [...] }`

2. **add_task({ text, due_date? })** — Adds a new task with optional due date.  
   Returns the updated list of tasks.

3. **mark_done({ task_id, done? })** — Marks a task as complete or incomplete.

All tool input/output schemas follow JSON Schema 2020‑12 and include `_meta.openai/outputTemplate` fields when connected to a UI.

## Persistence
Tasks are persisted in `data/tasks.json` with a structure like:
```json
{ "tasks": [ { "id": "...", "text": "Buy milk", "done": false } ] }
```
This simple JSON datastore can be replaced later with SQLite, Supabase, or another database backend.

## Running Locally
Install dependencies and run the app locally:
```bash
pip install fastapi uvicorn pydantic
python main.py
```
Example curl commands:
```bash
curl -X POST http://localhost:8000/mcp/tools/list
curl -X POST http://localhost:8000/mcp/tools/execute -d '{"tool":"get_tasks","args":{}}' -H "Content-Type: application/json"
```

## Deploying to mcp‑agent Cloud
1. Create an agent in mcp‑agent Cloud.  
2. Upload this repository or container image.  
3. Expose the `/mcp` HTTP endpoint.  
4. Register the endpoint URL in your ChatGPT App manifest.

## Widget Integration (Apps SDK)
Attach a React widget UI by specifying in the tool schema:
```json
"_meta": { "openai/outputTemplate": "ui://widget/todo.html" }
```
Host the corresponding HTML/JS widget asset to provide an interactive interface.

## Compliance Notes
- Adheres to the “1–2 actions per tool call” design pattern.  
- Uses structured JSON inputs and outputs for clarity and validation.  
- Supports HTTP transport compatible with the OpenAI Apps SDK.  
- Stateless beyond the persisted JSON data store.

## License & Credits
MIT License.  
Author: Hanieh + ChatGPT build guide.  
References: [OpenAI Apps SDK Docs](https://developers.openai.com/apps-sdk) and [Model Context Protocol](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports).
