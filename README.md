# LastautAI

**Natural Language to Workflow Automation** — Record your screen activity, let AI detect patterns, and generate deployable n8n workflows or execute them live with Claude.

## What It Does

1. **Record** your screen activity (mouse clicks, app switches)
2. **AI analyzes** the patterns and suggests automatable workflows
3. **Generate** structured n8n workflows from natural language descriptions
4. **Deploy** directly to an n8n instance or **execute live** with Claude AI tool use

## Architecture

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────┐
│  Single-Page  │────▶│  FastAPI Backend  │────▶│  Claude AI   │
│  Frontend     │◀────│  (Python 3.11+)  │◀────│  (Haiku)     │
└──────────────┘     └──────────────────┘     └─────────────┘
                              │
                     ┌────────┼────────┐
                     ▼        ▼        ▼
               ┌─────────┐ ┌──────┐ ┌───────┐
               │ SQLite   │ │ n8n  │ │ Slack │
               │ Database │ │ API  │ │Webhook│
               └─────────┘ └──────┘ └───────┘
```

- **Frontend**: Single HTML file (`ui/index.html`) — 4-tab SPA with dark theme
- **Backend**: FastAPI with SQLAlchemy ORM, JWT auth
- **AI**: Claude Haiku for screen analysis, workflow generation (4-stage pipeline), and live execution via tool use
- **Database**: SQLite (local development)

## Quick Start

### Prerequisites

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/)

### Setup

```bash
# Clone the repo
git clone https://github.com/AdrianosEB/LastautAI.git
cd LastautAI

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e .

# Set your API key
export ANTHROPIC_API_KEY="sk-ant-..."

# (Optional) Set Slack webhook for live execution
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."

# Start the server
uvicorn src.api.server:app --reload --port 8000
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

### First Run

1. **Sign up** — create an account (data is local to your machine)
2. **Create Workflow** tab — type a description or click an example chip
3. **Generate Workflow** — watch the 4-stage AI pipeline
4. **Run with AI** — see Claude execute it step-by-step in the live overlay
5. **Deploy to n8n** — push the workflow to your n8n instance

## Features

### Screen Recording & AI Analysis
Record your desktop activity. The recorder uses `pynput` for mouse click events and macOS `osascript` for active app/window detection. Events are flushed every 60 seconds to Claude Haiku for pattern analysis, which identifies repeatable tasks and suggests automations. Suggestions appear in the **Suggested** tab.

### 4-Stage Workflow Generation Pipeline
Natural language descriptions are processed through:
1. **Parser** — extracts actions, entities, and triggers
2. **Analyzer** — resolves actions, flags ambiguities
3. **Planner** — builds a DAG and assigns triggers
4. **Serializer** — produces final workflow JSON

### AI Execution (Run with AI)
Claude executes workflows live using tool use. Available tools:

| Tool | Status | Details |
|------|--------|---------|
| `fetch_url` | Real | Makes actual HTTP requests to any URL |
| `send_slack_message` | Real | Posts to Slack via webhook (requires `SLACK_WEBHOOK_URL`). Simulated if env var not set |
| `transform_data` | Real | Uses Claude to process/transform data per instruction |
| `check_condition` | Real | Evaluates conditions via Claude for branching logic |
| `send_email` | Simulated | Logs email details locally. Connect SendGrid/SES for production |
| `create_document` | Real | Generates document content with title and body |
| `log_result` | Real | Logs final workflow output |

### Scheduled Execution
Workflows with cron triggers can be scheduled via `POST /workflows/{id}/schedule`. The scheduler parses cron expressions (e.g. `0 9 * * 1-5` for weekdays at 9am) and simple intervals (`every 5m`), then runs the workflow on a recurring background thread using the AI execution engine. List active schedules with `GET /workflows/schedules`.

### Webhook Triggers
Saved workflows can be triggered externally via `POST /workflows/{id}/trigger`. Any system (n8n, Zapier, cron, curl) can send a JSON payload that gets injected as context into the AI execution engine. This enables event-driven automation without manual intervention.

### n8n Integration
Deploy generated workflows directly to any n8n instance via its REST API. Workflows are converted to n8n node format with proper connections and triggers.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/signup` | Create account |
| POST | `/auth/login` | Login, returns JWT |
| GET | `/auth/me` | Current user info |
| POST | `/workflows/generate` | Generate workflow from description |
| POST | `/workflows/generate-steps` | Generate with pipeline stage breakdown |
| POST | `/workflows/validate` | Validate workflow JSON |
| POST | `/workflows/run` | Generate and execute immediately |
| POST | `/workflows/execute-ai` | Execute with Claude tool use (SSE stream) |
| GET | `/workflows/history` | List saved workflows |
| GET | `/workflows/history/{id}` | Get workflow details |
| DELETE | `/workflows/history/{id}` | Delete workflow |
| POST | `/workflows/{id}/trigger` | Webhook trigger — execute a saved workflow with payload (no auth) |
| POST | `/workflows/{id}/schedule` | Start recurring execution from workflow's cron trigger |
| DELETE | `/workflows/{id}/schedule` | Stop a scheduled workflow |
| GET | `/workflows/schedules` | List all active schedules |
| POST | `/n8n/deploy` | Deploy to n8n instance |
| POST | `/capture/start` | Start screen recording |
| POST | `/capture/stop` | Stop screen recording |
| GET | `/capture/status` | Check recording status |
| GET | `/capture/suggestions` | List AI suggestions |
| POST | `/capture/suggestions/{id}` | Approve/dismiss suggestion |
| DELETE | `/capture/suggestions/{id}` | Delete suggestion |

## Project Structure

```
├── src/
│   ├── api/
│   │   ├── server.py          # FastAPI app setup, CORS, error handling
│   │   ├── routes/
│   │   │   ├── workflows.py   # generate, generate-steps, validate, run (consolidated)
│   │   │   ├── execute_ai.py  # Claude AI execution with tool use and conditional branching
│   │   │   ├── auth.py        # Authentication (signup/login/me)
│   │   │   ├── capture.py     # Screen recording & suggestions
│   │   │   ├── history.py     # Workflow CRUD
│   │   │   └── n8n.py         # n8n deployment
│   │   └── models/
│   │       └── requests.py    # Pydantic request models
│   ├── auth/                  # JWT & password hashing
│   ├── capture/
│   │   ├── recorder.py        # Screen activity recorder (pynput + osascript)
│   │   └── analyzer.py        # Claude-powered event analysis
│   ├── db/
│   │   ├── database.py        # SQLAlchemy setup
│   │   └── models.py          # User, Workflow, EventLog, WorkflowSuggestion
│   ├── executor/
│   │   ├── engine.py          # Step-by-step workflow executor with condition evaluation
│   │   └── actions.py         # Tool implementations (HTTP, email, etc.)
│   ├── scheduler.py             # In-memory cron scheduler (recurring workflow execution)
│   ├── utils/
│   │   ├── ai_client.py       # Shared Anthropic client singleton
│   │   └── parsing.py         # LLM response parsing (markdown fence stripping, JSON extraction)
│   └── pipeline/              # 4-stage NL-to-workflow pipeline
│       ├── parser.py
│       ├── analyzer.py
│       ├── planner.py
│       └── serializer.py
├── ui/
│   └── index.html             # Single-page frontend
├── schemas/
│   └── workflow.schema.json   # Workflow JSON schema
├── pyproject.toml
└── README.md
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `SLACK_WEBHOOK_URL` | No | Slack incoming webhook for `send_slack_message` tool (simulated if not set) |
| `JWT_SECRET` | No | JWT signing secret (auto-generated if not set) |

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, Uvicorn
- **AI**: Anthropic Claude (Haiku) — screen analysis, workflow generation, tool-use execution
- **Frontend**: Vanilla HTML/CSS/JS (single file, dark theme)
- **Database**: SQLite
- **Integrations**: n8n REST API, Slack Webhooks

## License

Built for the Claude AI Hackathon 2025.
