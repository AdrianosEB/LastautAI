# Project Backlog: Natural Language to Workflow Automation

## Project Structure

```
├── docs/
│   ├── prompts.md                          # Prompt design for the NL-to-workflow system
│   ├── vision.md                           # Product vision and design principles
│   ├── spec.md                             # Software engineering specification
│   └── backlog.md                          # This file — structure + task backlog
│
├── src/
│   ├── api/
│   │   ├── server.py                       # FastAPI app setup, middleware, CORS
│   │   ├── routes/
│   │   │   ├── workflows.py               # generate, generate-steps, validate, run (consolidated)
│   │   │   ├── execute_ai.py              # POST /workflows/execute-ai — Claude tool-use with conditional branching
│   │   │   ├── auth.py                     # POST /auth/signup, /login, GET /me
│   │   │   ├── capture.py                  # Screen recording & suggestion management
│   │   │   ├── history.py                  # GET/DELETE /workflows/history — workflow CRUD
│   │   │   └── n8n.py                      # POST /n8n/deploy — deploy to n8n instance
│   │   └── models/
│   │       └── requests.py                 # Pydantic models for API request bodies
│   │
│   ├── pipeline/
│   │   ├── __init__.py                     # Pipeline orchestrator — chains parser → analyzer → planner → serializer
│   │   ├── parser.py                       # NLP extraction: actions, entities, temporal cues, conditionals
│   │   ├── analyzer.py                     # Ambiguity resolution, action mapping, entity reference resolution
│   │   ├── planner.py                      # DAG construction, trigger assignment, parameter extraction
│   │   └── serializer.py                   # DAG → JSON/YAML output, schema validation before return
│   │
│   ├── catalog/
│   │   ├── registry.py                     # Action catalog loader and lookup logic
│   │   └── actions/
│   │       ├── fetch_data.yaml             # Action definition: fetch/pull/retrieve data from a source
│   │       ├── transform_data.yaml         # Action definition: filter/aggregate/summarize data
│   │       ├── send_email.yaml             # Action definition: send/email/notify via email
│   │       ├── send_notification.yaml      # Action definition: notify/alert via Slack, SMS, etc.
│   │       ├── write_file.yaml             # Action definition: save/write/export to file
│   │       └── http_request.yaml           # Action definition: call/request/post to an HTTP endpoint
│   │
│   ├── graph/
│   │   ├── dag.py                          # DAG data structure: nodes, edges, conditional edges
│   │   └── topological.py                  # Topological sort for serialization ordering
│   │
│   ├── db/
│   │   ├── database.py                     # SQLAlchemy engine, session factory, init_db()
│   │   └── models.py                       # User, Workflow, EventLog, WorkflowSuggestion ORM models
│   │
│   ├── auth/
│   │   ├── hashing.py                      # bcrypt password hashing/verification
│   │   ├── jwt.py                          # JWT token creation and validation
│   │   └── dependencies.py                 # FastAPI dependency: get_current_user from token
│   │
│   ├── capture/
│   │   ├── recorder.py                     # ScreenRecorder thread: mouse clicks, app switches via pynput
│   │   └── analyzer.py                     # Claude Haiku pattern analysis on event batches
│   │
│   ├── executor/
│   │   ├── engine.py                       # Step-by-step workflow executor with condition evaluation
│   │   └── actions.py                      # Action executors: HTTP, email, Slack, file, Claude-powered transforms
│   │
│   ├── utils/
│   │   ├── ai_client.py                    # Shared Anthropic client singleton
│   │   └── parsing.py                      # LLM response parsing (markdown fence stripping, JSON extraction)
│   │
│   └── prompts/
│       ├── system_prompt.txt               # System prompt for LLM-based parsing (Claude API)
│       ├── extraction_prompt.txt           # Prompt template for intent/entity/action extraction
│       └── disambiguation_prompt.txt       # Prompt template for resolving ambiguous input
│
├── schemas/
│   └── workflow.schema.json                # JSON Schema for the workflow definition output
│
├── examples/
│   ├── inputs/                             # Natural language workflow descriptions
│   └── outputs/                            # Expected structured workflow JSON outputs
│
├── ui/
│   └── index.html                          # Single-page web UI — login, dashboard, workflow create, AI execution
│
├── pyproject.toml                          # Project metadata, dependencies, scripts
└── .gitignore
```

---

## Backlog

Tasks are grouped by phase (matching spec.md milestones) and ordered by dependency. Each task is a concrete, completable unit of work.

### Phase 0 — Project Setup

- [x] **P0-1**: Initialize the repository with `pyproject.toml`, `.gitignore`
- [x] **P0-2**: Add core dependencies — `fastapi`, `uvicorn`, `pydantic`, `pyyaml`, `anthropic`, `pytest`, `httpx`
- [x] **P0-3**: Create the folder structure as defined above
- [x] **P0-4**: Set up `pytest` configuration in `pyproject.toml` with test paths and markers
- [x] **P0-5**: Create a basic FastAPI app in `src/api/server.py` that starts and returns health check at `GET /health`

### Phase 1 — Data Models, Schemas, and Action Catalog

- [x] **P1-1**: Define the workflow output JSON Schema in `schemas/workflow.schema.json` matching spec section 3.2
- [x] **P1-4**: Create Pydantic request models in `src/api/models/requests.py` — `GenerateRequest` and `ValidateRequest`
- [x] **P1-6**: Write the action catalog YAML format and create action definitions
- [x] **P1-7**: Create remaining starter action definitions
- [x] **P1-8**: Build `src/catalog/registry.py` — load all YAML files, index by action_id, provide `lookup()` method

### Phase 2 — Parser and Analyzer

- [x] **P2-1**: Write the system prompt in `src/prompts/system_prompt.txt`
- [x] **P2-2**: Write the extraction prompt template in `src/prompts/extraction_prompt.txt`
- [x] **P2-3**: Write the disambiguation prompt in `src/prompts/disambiguation_prompt.txt`
- [x] **P2-4**: Implement `src/pipeline/parser.py` — call Claude API, parse response into typed `ParseResult` dataclass
- [x] **P2-6**: Implement `src/pipeline/analyzer.py` — resolve actions against catalog, detect ordering, flag ambiguities
- [x] **P2-8**: Create example pairs in `examples/inputs/` and `examples/outputs/`

### Phase 3 — Graph and Planner

- [x] **P3-1**: Implement `src/graph/dag.py` — DAG class with node/edge operations and cycle detection
- [x] **P3-2**: Implement `src/graph/topological.py` — topological sort using Kahn's algorithm
- [x] **P3-4**: Implement `src/pipeline/planner.py` — build DAG, assign triggers, extract parameters, attach error handling

### Phase 4 — Serializer and API Endpoints

- [x] **P4-1**: Implement `src/pipeline/serializer.py` — walk DAG in topological order, validate against JSON Schema
- [x] **P4-3**: Implement `src/pipeline/__init__.py` — `generate_workflow()` and `generate_workflow_steps()` orchestrators
- [x] **P4-4**: Implement `POST /workflows/generate` in `src/api/routes/generate.py`
- [x] **P4-5**: Implement `POST /workflows/validate` in `src/api/routes/validate.py`
- [x] **P4-6**: Register all route modules in `src/api/server.py`

### Phase 5 — Golden Tests, Remaining Examples, and Polish

- [x] **P5-1**: Create remaining example inputs and outputs (5 pairs total)
- [x] **P5-4**: Add structured logging to the pipeline with timing
- [x] **P5-5**: Add request-level error handling middleware in `src/api/server.py`

### Phase 6 — Web UI and Export

- [x] **P6-1**: Create `POST /workflows/generate-steps` endpoint with intermediate results from each pipeline stage
- [x] **P6-2**: Build single-page web UI in `ui/index.html` — text area, pipeline visualization, summary cards, JSON viewer
- [x] **P6-3**: Add n8n format conversion in the UI — client-side mapping to n8n node types and connections
- [x] **P6-4**: Add example input chips for quick experimentation
- [x] **P6-5**: Serve the UI at `GET /` from FastAPI, add CORS middleware
- [x] **P6-6**: Add copy-to-clipboard and download-as-file functionality

### Phase 7 — User Accounts, Database, and Dashboard

- [x] **P7-1**: Add `sqlalchemy`, `passlib[bcrypt]`, `python-jose[cryptography]` to `pyproject.toml`
- [x] **P7-2**: Create `src/db/database.py` — SQLAlchemy engine, session factory, `init_db()`
- [x] **P7-3**: Create `src/db/models.py` — User, Workflow, EventLog, WorkflowSuggestion ORM models
- [x] **P7-4**: Create `src/auth/hashing.py` — bcrypt hash and verify functions
- [x] **P7-5**: Create `src/auth/jwt.py` — JWT token creation and validation with 24h expiry
- [x] **P7-6**: Create `src/auth/dependencies.py` — `get_current_user` and `get_optional_user` dependencies
- [x] **P7-7**: Create `POST /auth/signup` route
- [x] **P7-8**: Create `POST /auth/login` route
- [x] **P7-9**: Create `GET /auth/me` route
- [x] **P7-10**: Create `GET /workflows/history` and `DELETE /workflows/history/{id}` routes
- [x] **P7-11**: Create `GET /workflows/history/{id}` route with user ownership check
- [x] **P7-12**: Update `POST /workflows/generate-steps` to save workflows for authenticated users
- [x] **P7-13**: Update `POST /n8n/deploy` to record n8n workflow ID on saved workflow
- [x] **P7-14**: Add login/signup screens, JWT persistence in localStorage
- [x] **P7-15**: Add dashboard layout with tabs: Record, Suggested, Create Workflow, My Workflows
- [x] **P7-16**: My Workflows tab with history list, n8n/Local badges, view and delete actions
- [x] **P7-17**: Add `data/` to `.gitignore`

### Phase 8 — Screen Recording, Pattern Detection, and Suggestions

- [x] **P8-1**: Add `pynput` to `pyproject.toml`
- [x] **P8-2**: Create `src/capture/recorder.py` — ScreenRecorder thread with pynput mouse listener, app switch detection, 60s flush interval
- [x] **P8-3**: Create `src/capture/analyzer.py` — Claude Haiku analysis of event batches, pattern-focused prompt
- [x] **P8-4**: Add `EventLog` and `WorkflowSuggestion` models to `src/db/models.py`
- [x] **P8-5**: Create `src/api/routes/capture.py` with start/stop/status/suggestions/approve/dismiss/delete endpoints
- [x] **P8-6**: Register capture router in `src/api/server.py`
- [x] **P8-7**: Record tab UI: start/stop button with pulsing indicator, timer, past sessions list
- [x] **P8-8**: Suggested tab UI: suggestion cards with Generate Workflow action (auto-refines pending suggestions)
- [x] **P8-9**: Handoff: Generate Workflow pre-populates Create tab with refined suggestion prompt

### Phase 9 — AI Execution Engine

- [x] **P9-1**: Create `src/api/routes/execute_ai.py` — SSE streaming endpoint with Claude tool-use loop
- [x] **P9-2**: Implement 6 execution tools: `fetch_url` (real HTTP), `send_slack_message` (real via webhook), `send_email` (simulated), `transform_data` (Claude-powered), `create_document`, `log_result`
- [x] **P9-3**: Add full-screen execution overlay to UI with live step-by-step feed and animations
- [x] **P9-4**: Wire "Run with AI" button on Create Workflow tab, enabled after workflow generation

### Phase 10 — n8n Integration

- [x] **P10-1**: Create `POST /n8n/deploy` endpoint — proxy workflow to n8n REST API with UUID node IDs
- [x] **P10-2**: Add n8n connection settings to UI (URL + API key inputs)
- [x] **P10-3**: Track n8n deployment status per workflow (n8n_id in database)
- [x] **P10-4**: Support n8n workflow deletion when deleting from history

### Phase 11 — Scheduled Execution

- [x] **P11-1**: Create `src/scheduler.py` — in-memory cron scheduler with threading
- [x] **P11-2**: Cron parser supporting standard expressions and simple intervals
- [x] **P11-3**: `POST /workflows/{id}/schedule` — start recurring execution
- [x] **P11-4**: `DELETE /workflows/{id}/schedule` — stop a schedule
- [x] **P11-5**: `GET /workflows/schedules` — list active schedules with status

### Not Implemented (Out of Scope)

These features are documented as stretch goals but are not built:

- [ ] YAML output tab in UI (backend supports YAML, UI only shows JSON and n8n format)
- [ ] Make (Integromat) format conversion
- [ ] Real email delivery via SMTP/SendGrid/SES (currently simulated with logging)
- [ ] Automated test suite (unit, integration, golden tests)
