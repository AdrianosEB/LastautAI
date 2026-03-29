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
Record your desktop activity. The recorder captures mouse clicks and app switches, then Claude analyzes the patterns to suggest automatable workflows. Suggestions appear in the **Suggested** tab.

### 4-Stage Workflow Generation Pipeline
Natural language descriptions are processed through:
1. **Parser** — extracts actions, entities, and triggers
2. **Analyzer** — resolves actions, flags ambiguities
3. **Planner** — builds a DAG and assigns triggers
4. **Serializer** — produces final workflow JSON

### AI Execution (Run with AI)
Claude executes workflows live using tool use. Available tools:
- `fetch_url` — real HTTP requests
- `send_slack_message` — posts to Slack via webhook
- `send_email` — email delivery (simulated)
- `transform_data` — data processing
- `create_document` — generate reports/summaries
- `log_result` — final output logging

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
│   │   ├── server.py          # FastAPI app setup
│   │   ├── routes/
│   │   │   ├── auth.py        # Authentication (signup/login/me)
│   │   │   ├── capture.py     # Screen recording & suggestions
│   │   │   ├── execute_ai.py  # Claude AI execution with tool use
│   │   │   ├── generate.py    # Workflow generation
│   │   │   ├── generate_steps.py  # Step-by-step generation
│   │   │   ├── history.py     # Workflow CRUD
│   │   │   ├── n8n.py         # n8n deployment
│   │   │   ├── run.py         # Generate + execute
│   │   │   └── validate.py    # Schema validation
│   │   └── models/
│   │       └── requests.py    # Pydantic request models
│   ├── auth/                  # JWT & password hashing
│   ├── capture/
│   │   ├── recorder.py        # Screen activity recorder (pynput)
│   │   └── analyzer.py        # Claude-powered event analysis
│   ├── db/
│   │   ├── database.py        # SQLAlchemy setup
│   │   └── models.py          # User, Workflow, EventLog, WorkflowSuggestion
│   ├── executor/
│   │   ├── engine.py          # Step-by-step workflow executor
│   │   └── actions.py         # Tool implementations (HTTP, email, etc.)
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
| `SLACK_WEBHOOK_URL` | No | Slack incoming webhook for AI execution |
| `JWT_SECRET` | No | JWT signing secret (auto-generated if not set) |

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, Uvicorn
- **AI**: Anthropic Claude (Haiku) — screen analysis, workflow generation, tool-use execution
- **Frontend**: Vanilla HTML/CSS/JS (single file, dark theme)
- **Database**: SQLite
- **Integrations**: n8n REST API, Slack Webhooks

## License

Built for the Claude AI Hackathon 2025.
