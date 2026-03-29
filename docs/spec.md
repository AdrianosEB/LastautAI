# Software Engineering Specification: Natural Language to Workflow Automation

## 1. Overview

This document translates the product vision into a concrete engineering specification for building the Natural Language to Workflow Automation system. It covers system architecture, component design, data models, APIs, and non-functional requirements.

## 2. System Architecture

```
┌─────────────┐     ┌──────────────────────────────────────────────┐     ┌──────────────┐
│             │     │              Core Pipeline                   │     │              │
│  Input API  │────>│  Parser → Analyzer → Planner → Serializer   │────>│  Output API  │
│             │     │                                              │     │              │
└─────────────┘     └──────────────────────────────────────────────┘     └──────────────┘
```

### Components

| Component      | Responsibility                                                                 |
|----------------|--------------------------------------------------------------------------------|
| **Input API**  | Accepts natural language input via REST endpoint; validates and normalizes text |
| **Parser**     | Extracts intent, entities, temporal cues, and conditional language from input   |
| **Analyzer**   | Resolves ambiguities, identifies control flow, maps entities to workflow concepts |
| **Planner**    | Constructs the ordered step graph with triggers, dependencies, and parameters  |
| **Serializer** | Converts the internal workflow representation into the output schema (JSON/YAML)|
| **Output API** | Returns the structured workflow definition to the caller                        |

## 3. Data Models

### 3.1 Input

```json
{
  "description": "string — free-form natural language input",
  "output_format": "json | yaml",
  "options": {
    "strict_mode": "boolean — if true, reject ambiguous input instead of assuming"
  }
}
```

### 3.2 Workflow Definition (Output)

```json
{
  "name": "string",
  "trigger": {
    "type": "schedule | event | manual | webhook",
    "config": {
      "cron": "string | null",
      "event_type": "string | null",
      "webhook_path": "string | null"
    }
  },
  "steps": [
    {
      "id": "string",
      "action": "string",
      "description": "string",
      "inputs": {
        "<key>": "<value | step_ref>"
      },
      "outputs": {
        "<key>": "<type>"
      },
      "dependencies": ["step_id"],
      "conditions": {
        "if": "string — expression evaluated at runtime"
      }
    }
  ],
  "parameters": [
    {
      "name": "string",
      "type": "string | number | boolean | array",
      "default": "any",
      "description": "string"
    }
  ],
  "error_handling": {
    "default_retry": {
      "max_attempts": "integer",
      "backoff": "fixed | exponential",
      "delay_seconds": "integer"
    },
    "on_failure": "stop | skip | notify",
    "step_overrides": {
      "<step_id>": {
        "max_attempts": "integer",
        "on_failure": "stop | skip | notify"
      }
    }
  },
  "assumptions": [
    "string — any assumptions made about ambiguous input"
  ]
}
```

### 3.3 Internal Representation

The Planner operates on a directed acyclic graph (DAG):

- **Nodes** represent steps (action + metadata).
- **Edges** represent data dependencies or execution ordering.
- **Conditional edges** carry a predicate that gates execution of the target node.

## 4. API Specification

### 4.1 `POST /workflows/generate`

Generate a workflow from a natural language description.

**Request**

| Field           | Type   | Required | Description                          |
|-----------------|--------|----------|--------------------------------------|
| `description`   | string | yes      | Natural language task description    |
| `output_format` | string | no       | `json` (default) or `yaml`          |
| `strict_mode`   | bool   | no       | Reject ambiguous input if `true`     |

**Response — 200 OK**

Returns the workflow definition as described in section 3.2.

**Response — 422 Unprocessable Entity**

Returned when `strict_mode` is `true` and the input is ambiguous.

```json
{
  "error": "ambiguous_input",
  "message": "string",
  "ambiguities": [
    {
      "text": "string — the ambiguous fragment",
      "options": ["string — possible interpretations"]
    }
  ]
}
```

### 4.2 `POST /workflows/validate`

Validate an existing workflow definition for structural correctness.

**Request** — A workflow definition object (section 3.2).

**Response — 200 OK**

```json
{
  "valid": true
}
```

**Response — 400 Bad Request**

```json
{
  "valid": false,
  "errors": [
    {
      "path": "string — JSON path to the invalid field",
      "message": "string"
    }
  ]
}
```

## 5. Processing Pipeline Detail

### 5.1 Parser

- Tokenize and perform NLP on the input text.
- Extract **action verbs** (pull, send, summarize, notify).
- Extract **entities** (CRM, email, manager, sales data).
- Extract **temporal cues** (every Monday, after step X completes, when a file is uploaded).
- Extract **conditional language** (if, unless, when, otherwise).

### 5.2 Analyzer

- Map extracted actions to a canonical action catalog (e.g. "email" and "send an email" both resolve to `send_email`).
- Resolve entity references ("the report" refers to the output of the summarize step).
- Detect implicit ordering (actions described sequentially imply serial execution).
- Flag ambiguities and record assumptions.

### 5.3 Planner

- Build the step DAG from analyzed actions and dependencies.
- Assign a trigger based on temporal cues or default to `manual`.
- Extract parameters from configurable values found in the text.
- Attach default error handling; apply step-level overrides where the input implies them (e.g. "retry up to 3 times").

### 5.4 Serializer

- Walk the DAG in topological order to produce the `steps` array.
- Serialize to the requested output format (JSON or YAML).
- Validate the output against the workflow schema before returning.

## 6. Action Catalog

The system maintains a catalog of recognized action types. Each entry defines:

| Field             | Description                                         |
|-------------------|-----------------------------------------------------|
| `action_id`       | Canonical identifier (e.g. `fetch_data`)            |
| `aliases`         | Natural language phrases that map to this action     |
| `required_inputs` | Inputs the action expects                           |
| `outputs`         | What the action produces                            |
| `service`         | External service or tool involved (if any)          |

The catalog is extensible — new actions can be registered without modifying the core pipeline.

## 7. Non-Functional Requirements

### 7.1 Performance

- Workflow generation should complete in under **3 seconds** for descriptions up to 500 words.
- The system should handle **50 concurrent requests** without degradation.

### 7.2 Reliability

- The pipeline must not produce invalid JSON/YAML. Output is schema-validated before being returned.
- If any pipeline stage fails, the system returns a structured error — never a partial workflow.

### 7.3 Extensibility

- New action types can be added to the catalog without code changes to the core pipeline.
- Output formats beyond JSON/YAML can be added by implementing a new serializer.
- The NLP layer should be swappable (e.g. replace a rule-based parser with an LLM-based one) without changing downstream components.

### 7.4 Testing

- **Unit tests** for each pipeline component (parser, analyzer, planner, serializer) in isolation.
- **Integration tests** that send natural language descriptions through the full pipeline and assert on the generated workflow structure.
- **Golden tests** — a curated set of input/output pairs that serve as regression tests for common workflow patterns.

## 8. Technology Considerations

| Concern           | Options                                                       |
|-------------------|---------------------------------------------------------------|
| Language          | Python (rich NLP ecosystem) or TypeScript (if targeting Node)  |
| NLP               | LLM-based extraction (Claude API) or spaCy for rule-based     |
| API framework     | FastAPI (Python) or Express/Hono (TypeScript)                  |
| Schema validation | JSON Schema / Pydantic (Python) or Zod (TypeScript)            |
| Output formats    | Built-in `json` module; `pyyaml` or `js-yaml` for YAML        |

## 9. Web User Interface

### 9.1 Architecture

The UI is a single-page HTML/CSS/JS application served directly by FastAPI at `GET /`. No separate frontend build step or framework is required — the HTML file is loaded from `ui/index.html`.

### 9.2 Step-by-Step Pipeline Endpoint

`POST /workflows/generate-steps` — Same input as `/workflows/generate`, but returns intermediate results from every pipeline stage:

```json
{
  "parser": {
    "status": "success",
    "duration_ms": 1230,
    "result": { "actions": [...], "entities": [...], "temporal_cues": [...] }
  },
  "analyzer": {
    "status": "success",
    "duration_ms": 12,
    "result": { "resolved_actions": [...], "ordering": [...], "assumptions": [...] }
  },
  "planner": {
    "status": "success",
    "duration_ms": 3,
    "result": { "dag": { "nodes": [...], "edges": [...] }, "trigger": {...} }
  },
  "serializer": {
    "status": "success",
    "duration_ms": 5
  },
  "workflow": { ... }
}
```

### 9.3 UI Features

| Feature                    | Description                                                           |
|----------------------------|-----------------------------------------------------------------------|
| Pipeline visualization     | Four stage cards with real-time status (pending/active/done/error)    |
| Intermediate results       | Each stage is expandable to inspect its output                        |
| Summary cards              | Trigger type, step count, and parameter count at a glance            |
| Dual output format         | Toggle between raw workflow JSON and n8n-compatible format            |
| n8n export                 | Client-side conversion to n8n workflow format with node mapping       |
| Copy / Download            | One-click clipboard copy or file download                            |
| Example inputs             | Pre-built chips for common workflow patterns                          |

### 9.4 n8n Format Conversion

The UI includes client-side conversion from the LastautAI workflow schema to n8n's workflow format:

| LastautAI action   | n8n node type                         |
|--------------------|---------------------------------------|
| `fetch_data`       | `n8n-nodes-base.httpRequest`          |
| `transform_data`   | `n8n-nodes-base.code`                |
| `send_email`       | `n8n-nodes-base.emailSend`           |
| `send_notification`| `n8n-nodes-base.slack`               |
| `write_file`       | `n8n-nodes-base.writeBinaryFile`     |
| `http_request`     | `n8n-nodes-base.httpRequest`         |

Trigger mapping: `schedule` → `scheduleTrigger`, `webhook` → `webhook`, others → `manualTrigger`.

## 10. User Accounts and Database

### 10.1 Database

SQLite via SQLAlchemy, stored at `data/lastautai.db`. Chosen for simplicity — no external database server required.

### 10.2 Schema

#### `users` table

| Column        | Type         | Constraints              |
|---------------|--------------|--------------------------|
| `id`          | INTEGER      | PRIMARY KEY, AUTOINCREMENT |
| `username`    | VARCHAR(50)  | UNIQUE, NOT NULL         |
| `email`       | VARCHAR(255) | UNIQUE, NOT NULL         |
| `password_hash` | VARCHAR(255) | NOT NULL               |
| `created_at`  | DATETIME     | DEFAULT now              |

#### `workflows` table

| Column          | Type         | Constraints              |
|-----------------|--------------|--------------------------|
| `id`            | INTEGER      | PRIMARY KEY, AUTOINCREMENT |
| `user_id`       | INTEGER      | FOREIGN KEY → users.id   |
| `name`          | VARCHAR(255) | NOT NULL                 |
| `description`   | TEXT         | NOT NULL (original NL input) |
| `workflow_json` | TEXT         | NOT NULL (generated JSON) |
| `n8n_id`        | VARCHAR(100) | NULL (set if deployed)   |
| `created_at`    | DATETIME     | DEFAULT now              |

### 10.3 Authentication

- **Signup**: `POST /auth/signup` — username, email, password → creates user, returns JWT
- **Login**: `POST /auth/login` — username, password → returns JWT
- **JWT**: Signed with a server-side secret (`AUTH_SECRET` env var), 24h expiry
- **Password hashing**: bcrypt via `passlib`
- **Protected routes**: All `/workflows/*` and `/n8n/*` endpoints require `Authorization: Bearer <token>` header

### 10.4 API Changes

| Endpoint                       | Auth Required | Change                                      |
|--------------------------------|---------------|----------------------------------------------|
| `POST /auth/signup`            | No            | New — create user account                    |
| `POST /auth/login`             | No            | New — authenticate and receive JWT           |
| `GET /auth/me`                 | Yes           | New — return current user info               |
| `POST /workflows/generate-steps` | Yes         | Now saves workflow to user's account         |
| `POST /n8n/deploy`             | Yes           | Now records n8n_id on the saved workflow     |
| `GET /workflows/history`       | Yes           | New — list user's saved workflows            |
| `GET /workflows/{id}`         | Yes           | New — retrieve a specific saved workflow     |

### 10.5 Dashboard UI

The UI transitions from a single-page tool to an authenticated dashboard:

| Section               | Status     | Description                                          |
|-----------------------|------------|------------------------------------------------------|
| Login / Signup        | Phase 7    | Gate access to the app                               |
| Create Workflow       | Existing   | The current type-in + generate + deploy flow         |
| My Workflows          | Phase 7    | List of previously generated workflows per user      |
| Record                | Phase 8    | Start/stop screen recording, view detected patterns  |
| Suggested Workflows   | Phase 8    | Approve/dismiss AI-detected patterns                 |

## 11. Screen Recording and Pattern Detection

### 11.1 Overview

The Record feature captures user desktop activity (mouse clicks, app switches) via a background thread and periodically sends event batches to Claude for pattern analysis. Detected patterns are surfaced as workflow suggestions that can be approved and sent through the NL-to-workflow pipeline.

This integrates the `LastautAI-screen-capture` project's recording backend into the FastAPI server.

### 11.2 Recording Architecture

```
User clicks "Start Recording"
        |
FastAPI starts ScreenRecorder thread (per-user, daemon)
        |
Continuous loop:
  - pynput.mouse.Listener captures clicks (with app context)
  - osascript polls for app switches every 1 second
  - Events buffered in memory
        |
Every 60 seconds:
  - Buffer flushed
  - Events saved to event_logs table
  - Events sent to Claude Haiku for analysis
  - If pattern found → saved to workflow_suggestions table
        |
Frontend polls GET /capture/suggestions every 30 seconds
        |
User sees suggestion cards → Approve or Dismiss
        |
Approved → description sent to Create Workflow pipeline
```

### 11.3 Database Tables (additions)

#### `event_logs` table

| Column        | Type         | Constraints              |
|---------------|--------------|--------------------------|
| `id`          | INTEGER      | PRIMARY KEY              |
| `user_id`     | INTEGER      | FOREIGN KEY → users.id   |
| `timestamp`   | DATETIME     | DEFAULT now              |
| `event_type`  | VARCHAR(50)  | NOT NULL (`click`, `app_switch`) |
| `app_name`    | VARCHAR(200) | NOT NULL                 |
| `window_title`| VARCHAR(500) | nullable                 |
| `detail`      | VARCHAR(500) | nullable (URL, file path, coords) |

#### `workflow_suggestions` table

| Column        | Type         | Constraints              |
|---------------|--------------|--------------------------|
| `id`          | INTEGER      | PRIMARY KEY              |
| `user_id`     | INTEGER      | FOREIGN KEY → users.id   |
| `created_at`  | DATETIME     | DEFAULT now              |
| `description` | TEXT         | NOT NULL (Claude's analysis) |
| `raw_events`  | TEXT         | NOT NULL (event log text) |
| `status`      | VARCHAR(20)  | DEFAULT `pending` (`pending`, `approved`, `dismissed`) |

### 11.4 Recording API Endpoints

| Endpoint                          | Auth | Description                                      |
|-----------------------------------|------|--------------------------------------------------|
| `POST /capture/start`             | Yes  | Start recording for current user                 |
| `POST /capture/stop`              | Yes  | Stop recording for current user                  |
| `GET /capture/status`             | Yes  | Return `{recording: true/false}`                 |
| `GET /capture/suggestions`        | Yes  | List pending suggestions for current user        |
| `POST /capture/suggestions/{id}`  | Yes  | Update suggestion status (approve/dismiss)       |

### 11.5 Event Capture Details

| App | What's captured | How |
|-----|-----------------|-----|
| Chrome/Chromium | Active tab URL | AppleScript |
| Safari | Current tab URL | AppleScript |
| Firefox | Window title | AppleScript |
| Finder | Folder path (POSIX) | AppleScript |
| Other apps | Click coordinates | pynput |

**Privacy:** Only app names, window titles, and coordinates. No passwords, no message content, no keystrokes.

### 11.6 Pattern Analysis

Events are formatted into a readable log and sent to Claude Haiku with a prompt that asks for:
- What the user is doing
- How often the pattern repeats
- Whether it could be automated

If no clear pattern is found, Claude responds with "Not enough data" and no suggestion is created.

### 11.7 Suggestion → Workflow Handoff

When a user approves a suggestion, its `description` text is used as the input to `POST /workflows/generate-steps`, feeding it through the existing Parser → Analyzer → Planner → Serializer pipeline. The generated workflow is saved to the user's account and can be deployed to n8n.

## 12. Testing Plan

### 12.1 Philosophy

Tests call functions directly with simulated inputs — no sleeping, no UI clicking, no waiting for timers. Each test targets one layer.

### 12.2 Test Matrix

| Test | Layer | What it checks | Requires API? |
|------|-------|----------------|---------------|
| 1 — Buffer | Recorder | Events land in buffer correctly | No |
| 2 — Analyzer | Claude API | Pattern analysis returns description | Yes (Haiku) |
| 3 — Flush | DB write | Events + suggestions saved to DB | Yes (Haiku) |
| 4 — Endpoints | API routes | Start/stop/suggestions return correct JSON | No (mock recorder) |
| 5 — End-to-end | Full pipeline | Inject events → flush → suggestion appears via API | Yes (Haiku) |
| 6 — Handoff | Suggestion → Generate | Approved suggestion feeds into NL pipeline | Yes (Sonnet) |

### 12.3 Test 1: Event Buffer

```python
from src.capture.recorder import ScreenRecorder

r = ScreenRecorder(user_id=1)
r._log('app_switch', 'Chrome', window_title='Gmail')
r._log('click', 'Chrome', detail='x=100 y=200')
r._log('app_switch', 'Finder', window_title='Downloads')

assert len(r.buffer) == 3
assert r.buffer[0]['event_type'] == 'app_switch'
assert r.buffer[1]['app_name'] == 'Chrome'
```

### 12.4 Test 2: Analyzer

```python
from src.capture.analyzer import analyze_events

fake_events = [
    {'timestamp': '09:01:00', 'event_type': 'app_switch', 'app_name': 'Chrome',
     'window_title': 'Gmail', 'detail': ''},
    {'timestamp': '09:01:10', 'event_type': 'click', 'app_name': 'Chrome',
     'window_title': '', 'detail': 'x=500 y=300'},
    {'timestamp': '09:01:20', 'event_type': 'app_switch', 'app_name': 'Finder',
     'window_title': 'Downloads', 'detail': ''},
]

result = analyze_events(fake_events)
assert isinstance(result, str)
assert len(result) > 0
```

### 12.5 Test 3: API Endpoints

```python
# POST /capture/start → {"status": "started"}
# POST /capture/stop  → {"status": "stopped"}
# GET /capture/suggestions → {"suggestions": [...]}
# POST /capture/suggestions/1 → {"status": "approved"}
```

### 12.6 Test 4: End-to-End

Inject fake events into a recorder, call flush, verify suggestion appears via the API, approve it, and verify it generates a workflow.

## 13. AI Execution Engine

### 13.1 Overview

In addition to generating workflow definitions, the system can execute workflows live using Claude's tool-use capability. This provides immediate, on-demand execution without requiring an external workflow engine.

### 13.2 Endpoint

`POST /workflows/execute-ai` — accepts a workflow description and optional workflow JSON, returns an SSE (Server-Sent Events) stream of execution progress.

### 13.3 Tool Catalog

| Tool | Implementation | Description |
|------|---------------|-------------|
| `fetch_url` | Real (httpx) | HTTP GET/POST/PUT/DELETE to any URL |
| `send_slack_message` | Real (webhook) | Post to Slack channel via `SLACK_WEBHOOK_URL` env var. Simulated if not set |
| `send_email` | Simulated | Logs email details. Connect SendGrid/SES for production delivery |
| `transform_data` | Real (Claude) | Claude processes data according to a natural language instruction |
| `check_condition` | Real (Claude) | Evaluates conditions for branching logic (e.g. "if data has errors") |
| `create_document` | Real | Generates document content with title, format, and body |
| `log_result` | Real | Logs the final workflow output |

### 13.4 Execution Loop

1. System prompt instructs Claude to execute the workflow step by step using available tools
2. Claude calls tools one at a time; each tool call and result is streamed as an SSE event
3. Tool results are fed back into the conversation for multi-turn execution
4. Loop terminates on `end_turn` or after 15 iterations (safety limit)

### 13.5 SSE Event Types

- `thinking` — Claude's reasoning text between tool calls
- `step_start` — tool invocation with name and input parameters
- `step_complete` — tool result after execution
- `error` — execution error
- `complete` — workflow finished

### 13.6 Webhook Triggers

Saved workflows can be executed via external HTTP POST to `POST /workflows/{id}/trigger`.

- No authentication required (webhook endpoint for external callers)
- Accepts JSON payload as triggering context
- Reuses the same SSE execution loop as `/execute-ai` via `run_workflow_stream()`
- Payload is injected into Claude's context so it can use the triggering data
- History endpoint includes `has_webhook` flag for workflows with webhook/event triggers

### 13.7 Scheduled Execution

Workflows with cron triggers can be scheduled for recurring execution via the scheduler module (`src/scheduler.py`).

**Endpoints:**
- `POST /workflows/{id}/schedule` — start recurring execution using the workflow's cron config
- `DELETE /workflows/{id}/schedule` — stop a schedule
- `GET /workflows/schedules` — list active schedules with run counts and last-run timestamps

**Cron parsing:** Supports standard 5-field cron expressions (`*/5 * * * *`, `0 9 * * 1-5`) and simple intervals (`every 5m`, `every 1h`). Minimum interval: 10 seconds.

**Architecture:** Background threads with `threading.Timer` loops. Each scheduled workflow runs in its own daemon thread, consuming `run_workflow_stream()` to execute via Claude's tool-use agent. In-memory storage (reset on server restart); production path would use Redis + Celery.

### 13.8 UI

A full-screen overlay displays the execution feed with animated step cards, showing each tool call, its inputs, and results in real time.

## 14. Milestones

| Phase | Deliverable                                                        |
|-------|--------------------------------------------------------------------|
| 1     | Data models, API contracts, and action catalog schema defined      |
| 2     | Parser and Analyzer — extract intent and actions from plain text   |
| 3     | Planner — build step DAG with triggers, dependencies, parameters   |
| 4     | Serializer and API — end-to-end workflow generation via REST       |
| 5     | Validation endpoint, golden test suite, and documentation          |
| 6     | Web UI with step-by-step visualization and n8n export              |
| 7     | User accounts, database, workflow history, and dashboard           |
| 8     | Screen recording, pattern detection, suggestions, and handoff      |
| 9     | AI execution engine — Claude tool-use with SSE streaming           |
| 10    | n8n integration — deploy, track, and delete workflows via REST API |
