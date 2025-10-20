# Deployment Guide

## Local Development

### 1. Install Dependencies
```bash
uv sync
```

### 2. Run the Server
```bash
uv run python main.py
```

The server will start on `http://localhost:8080`

### 3. Access the UI
Open your browser to:
- Widget UI: http://localhost:8080/static/todo.html
- API Root: http://localhost:8080/

### 4. Test the MCP Endpoints
```bash
# List available tools
curl -X POST http://localhost:8080/mcp/tools/list

# Add a task
curl -X POST http://localhost:8080/mcp/tools/execute \
  -H "Content-Type: application/json" \
  -d '{"name":"add_task","arguments":{"text":"Buy groceries"}}'

# Get all tasks
curl -X POST http://localhost:8080/mcp/tools/execute \
  -H "Content-Type: application/json" \
  -d '{"name":"get_tasks","arguments":{}}'

# Mark a task as done
curl -X POST http://localhost:8080/mcp/tools/execute \
  -H "Content-Type: application/json" \
  -d '{"name":"mark_done","arguments":{"task_id":"YOUR_TASK_ID","done":true}}'
```

---

## Deploy to mcp-agent Cloud

### Prerequisites
The app is already configured for mcp-agent cloud deployment with:
- [mcp_agent.config.yaml](mcp_agent.config.yaml) - Configuration file
- [main.py](main.py) - MCPApp-based server with FastMCP tools

### 1. Authenticate
```bash
uv run mcp-agent login
```

### 2. Deploy Your App
```bash
uv run mcp-agent deploy --no-auth
```

This will:
- Package your application
- Upload to mcp-agent Cloud
- Provide you with a deployment URL like: `https://<deployment-id>.deployments.mcp-agent.com/sse`

### 3. Important Notes
- Your deployment URL will end with `/sse` - this is the SSE (Server-Sent Events) endpoint
- Save this URL for connecting to ChatGPT
- The app uses asyncio execution engine (configured in [mcp_agent.config.yaml](mcp_agent.config.yaml))

### 4. Update Your Deployment
When you make changes, redeploy:
```bash
uv run mcp-agent deploy --no-auth
```

---

## Connect to ChatGPT (OpenAI Apps SDK)

### 1. Get Your Server URL
After deploying to mcp-agent Cloud, you'll receive a URL like:
```
https://<deployment-id>.deployments.mcp-agent.com/sse
```

**IMPORTANT**: Make sure the URL ends with `/sse`

### 2. Add to ChatGPT Developer Mode
1. Open ChatGPT (https://chat.openai.com)
2. Enable Developer Mode:
   - Go to Settings → Beta Features
   - Enable "Developer Mode"
3. Go to Settings → Connectors
4. Click "Add Connector"
5. Paste your deployment URL (with `/sse` at the end)
6. Save

### 3. Test Your App
Test your tools with natural language in ChatGPT:
- "Show me my tasks"
- "Add a task to buy milk"
- "Mark the first task as done"
- "Add a task to call mom with due date 2025-10-20"

### 4. Debug with MCP Inspector (Optional)
Use the MCP Inspector to test your server:
```bash
npx @modelcontextprotocol/inspector https://<deployment-id>.deployments.mcp-agent.com/sse
```

### 5. Submit for Review
Once testing is complete:
1. Go to OpenAI Apps Dashboard
2. Submit your app with demo credentials
3. Provide clear app description and use cases
4. Wait for review approval
5. Your app will be available to 800M+ ChatGPT users!

---

## Environment Variables (Optional)

Create a `.env` file for configuration:
```env
DATA_DIR=./data
PORT=8080
```

Update [main.py](main.py) to load these:
```python
import os
from dotenv import load_dotenv

load_dotenv()
PORT = int(os.getenv("PORT", 8080))
```

---

## Production Considerations

### Security
- Add authentication/authorization
- Validate user permissions
- Rate limit API endpoints
- Use HTTPS only

### Data
- Replace JSON file storage with PostgreSQL/MongoDB
- Implement proper backup strategy
- Add database migrations

### Monitoring
- Add logging with structured logs
- Set up error tracking (Sentry, etc.)
- Monitor performance metrics
- Set up health check endpoints

### Scaling
- mcp-agent Cloud handles auto-scaling
- Consider caching frequently accessed data
- Optimize database queries

---

## Troubleshooting

### Server won't start
- Check if port 8080 is already in use
- Verify all dependencies are installed: `uv sync`
- Check for syntax errors: `uv run python -m py_compile main.py`

### Tools not working
- Verify MCP endpoints respond: `curl http://localhost:8080/mcp/tools/list`
- Check server logs for errors
- Validate JSON payload format

### Deployment fails
- Ensure you're authenticated: `mcp-agent cloud auth login`
- Check your internet connection
- Verify app name is valid (lowercase, hyphens only)

### ChatGPT can't connect
- Verify your server URL is publicly accessible
- Check CORS settings allow ChatGPT domain
- Ensure `/mcp/tools/list` returns valid tool descriptors

---

## Support

- OpenAI Apps SDK Docs: https://developers.openai.com/apps-sdk/
- MCP Agent Cloud Docs: https://docs.mcp-agent.com/
- Model Context Protocol: https://modelcontextprotocol.io/
