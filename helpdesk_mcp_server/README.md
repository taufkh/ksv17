# Helpdesk MCP Server

Connects Claude (Cowork / Claude Code) directly to your Odoo 17 helpdesk via
the **Model Context Protocol (MCP)**.  Developers can ask Claude to browse
tickets, read AI-generated development plans, post notes, and update ticket
status — without opening Odoo.

---

## Architecture Overview

```
Customer submits ticket
        │
        ▼
  Odoo Helpdesk (helpdesk_mgmt)
        │
        ▼  (cron every 5 min OR manual button)
  helpdesk_custom_claude_ai module
        │
        ▼  HTTP POST → https://api.anthropic.com/v1/messages
  Claude AI (Anthropic API)
        │
        ├─► CONFIGURATION_QUERY → auto-reply to customer chatter
        │
        └─► BUG_REPORT / FEATURE_REQUEST → dev plan as internal note
                │
                ▼
        MCP Server (this project)
                │
                ▼  stdio / SSE
        Claude in Cowork / Claude Code
                │
                ▼
        Developer reads plan, gets guidance, asks questions
```

---

## Quick Start

### 1. Install dependencies

```bash
cd helpdesk_mcp_server
pip install -r requirements.txt
```

### 2. Configure connection

```bash
cp .env.example .env
# Edit .env with your Odoo URL, database, username, and password
```

### 3. Add to Claude Code (stdio)

In your Claude Code MCP config (`~/.claude/claude_desktop_config.json` or
`.mcp.json` in the project root):

```json
{
  "mcpServers": {
    "odoo-helpdesk": {
      "command": "python",
      "args": ["/path/to/helpdesk_mcp_server/server.py"],
      "env": {
        "ODOO_URL": "http://localhost:8069",
        "ODOO_DB": "your_db",
        "ODOO_USERNAME": "admin",
        "ODOO_PASSWORD": "your_password"
      }
    }
  }
}
```

### 4. Add to Cowork (Claude desktop)

Go to **Settings → MCP Servers → Add** and paste the same config above.

### 5. Remote / SSE mode

For team-shared access over HTTP:

```bash
MCP_TRANSPORT=sse MCP_PORT=8765 python server.py
```

Point Claude to `http://your-server:8765/sse`.

---

## Available MCP Tools

| Tool | Description |
|------|-------------|
| `list_tickets` | List tickets with filters (status, AI state, team) |
| `get_ticket` | Full ticket details including description and AI analysis |
| `get_development_plan` | Read Claude's HTML dev plan as formatted plain text |
| `get_customer_response` | Read Claude's customer-facing answer |
| `post_message_to_ticket` | Post public reply or internal note to chatter |
| `get_ticket_messages` | Read recent chatter messages |
| `update_ticket` | Change stage / priority / assignee + optional note |
| `trigger_ai_analysis` | Queue ticket for Claude re-analysis |
| `list_dev_plan_tickets` | List all open tickets with ready dev plans |
| `get_ai_dashboard` | AI stats: counts by status across all teams |
| `list_teams` | Show teams and their AI configuration |

## MCP Resources

| Resource URI | Description |
|---|---|
| `helpdesk://overview` | AI dashboard summary |
| `helpdesk://pending-dev-plans` | All tickets with dev plans |

---

## Example Developer Workflow in Cowork

> **Developer:** "Show me all tickets with development plans ready"
> → Claude calls `list_dev_plan_tickets()`

> **Developer:** "Give me the full plan for ticket HD00042"
> → Claude calls `get_development_plan("HD00042")`

> **Developer:** "Post an internal note that I'm starting work on HD00042"
> → Claude calls `post_message_to_ticket("HD00042", "Starting implementation...", internal=True)`

> **Developer:** "Move HD00042 to In Progress and assign it to me"
> → Claude calls `update_ticket("HD00042", stage_name="In Progress", assignee_login="taufkh")`

---

## Odoo Module: helpdesk_custom_claude_ai

The companion Odoo module must be installed for AI fields and analysis to work.

### Installation

1. Copy `helpdesk_custom_claude_ai/` into your Odoo addons path
2. Restart the Odoo service
3. Upgrade the module list and install **Helpdesk AI Assistant (Claude)**
4. Go to **Settings → Helpdesk AI** and enter your Anthropic API key
5. Go to **Helpdesk → Configuration → Teams**, open a team, and enable
   Claude AI in the **Claude AI** tab
6. Fill in the **Project Context** field — this is the most important step
   for getting accurate, project-specific answers

### Anthropic API Key

Get a key at [console.anthropic.com](https://console.anthropic.com/).
The module uses the **Messages API** via plain HTTPS — no extra Python
packages are required (uses `requests`, already in Odoo's stack).

### Recommended Claude Model

`claude-sonnet-4-6` — best quality/cost balance for helpdesk classification.
Switch to `claude-haiku-4-5-20251001` for high ticket volumes on a tight budget.

---

## Security Notes

- The MCP server uses Odoo's XML-RPC with the configured user's access rights
- Use a dedicated Odoo user with **Helpdesk Manager** group only
- For production SSE deployments: put the server behind nginx with HTTPS + IP allowlist
- The Anthropic API key is stored in `ir.config_parameter` (Odoo system parameters), not in code
