# Project Backlog: Natural Language to Workflow Automation

## Project Structure

```
workflow-automation/
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
│   │   │   ├── generate.py                 # POST /workflows/generate endpoint
│   │   │   ├── generate_steps.py           # POST /workflows/generate-steps — step-by-step with intermediate results
│   │   │   ├── run.py                      # POST /workflows/run — generate + execute
│   │   │   └── validate.py                 # POST /workflows/validate endpoint
│   │   └── models/
│   │       ├── requests.py                 # Pydantic models for API request bodies
│   │       └── responses.py                # Pydantic models for API responses and errors
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
│   │   └── models.py                       # User and Workflow ORM models
│   │
│   ├── auth/
│   │   ├── hashing.py                      # bcrypt password hashing/verification
│   │   ├── jwt.py                          # JWT token creation and validation
│   │   └── dependencies.py                 # FastAPI dependency: get_current_user from token
│   │
│   └── prompts/
│       ├── system_prompt.txt               # System prompt for LLM-based parsing (Claude API)
│       ├── extraction_prompt.txt           # Prompt template for intent/entity/action extraction
│       └── disambiguation_prompt.txt       # Prompt template for resolving ambiguous input
│
├── schemas/
│   ├── workflow.schema.json                # JSON Schema for the workflow definition output
│   ├── action.schema.json                  # JSON Schema for action catalog entries
│   └── api_error.schema.json              # JSON Schema for structured API error responses
│
├── examples/
│   ├── inputs/
│   │   ├── simple_report.txt               # "Every Monday, pull sales data and email the team"
│   │   ├── conditional_alert.txt           # "When CPU > 90%, restart the service and notify oncall"
│   │   ├── multi_step_pipeline.txt         # "Fetch logs, filter errors, summarize, post to Slack"
│   │   ├── webhook_trigger.txt             # "When a new order comes in, validate it and update inventory"
│   │   └── parameterized_etl.txt           # "Daily at 6am, pull data from {source}, transform, load to {dest}"
│   └── outputs/
│       ├── simple_report.json              # Expected workflow output for simple_report.txt
│       ├── conditional_alert.json          # Expected workflow output for conditional_alert.txt
│       ├── multi_step_pipeline.json        # Expected workflow output for multi_step_pipeline.txt
│       ├── webhook_trigger.json            # Expected workflow output for webhook_trigger.txt
│       └── parameterized_etl.json          # Expected workflow output for parameterized_etl.txt
│
├── tests/
│   ├── unit/
│   │   ├── test_parser.py                  # Parser extraction tests (actions, entities, time, conditions)
│   │   ├── test_analyzer.py                # Analyzer tests (alias resolution, ambiguity flagging)
│   │   ├── test_planner.py                 # Planner tests (DAG structure, trigger assignment, params)
│   │   ├── test_serializer.py              # Serializer tests (JSON/YAML output, schema compliance)
│   │   ├── test_dag.py                     # DAG data structure tests (add/remove nodes, cycle detection)
│   │   └── test_catalog.py                 # Action catalog loading and lookup tests
│   ├── integration/
│   │   ├── test_pipeline.py                # End-to-end: NL input → workflow output
│   │   └── test_api.py                     # HTTP-level tests for both endpoints
│   └── golden/
│       └── test_golden.py                  # Runs all examples/inputs through pipeline, diffs against examples/outputs
│
├── data/
│   └── lastautai.db                        # SQLite database (gitignored, created at runtime)
│
├── ui/
│   └── index.html                          # Single-page web UI — login, dashboard, workflow create, n8n export
│
├── pyproject.toml                          # Project metadata, dependencies, scripts
├── .env.example                            # Template for environment variables (API keys, config)
└── .gitignore
```

---

## Backlog

Tasks are grouped by phase (matching spec.md milestones) and ordered by dependency. Each task is a concrete, completable unit of work.

### Phase 0 — Project Setup

- [ ] **P0-1**: Initialize the repository with `pyproject.toml`, `.gitignore`, and `.env.example`
- [ ] **P0-2**: Add core dependencies — `fastapi`, `uvicorn`, `pydantic`, `pyyaml`, `anthropic`, `pytest`, `httpx`
- [ ] **P0-3**: Create the folder structure as defined above (empty `__init__.py` files where needed)
- [ ] **P0-4**: Set up `pytest` configuration in `pyproject.toml` with test paths and markers
- [ ] **P0-5**: Create a basic FastAPI app in `src/api/server.py` that starts and returns health check at `GET /health`

### Phase 1 — Data Models, Schemas, and Action Catalog

- [ ] **P1-1**: Define the workflow output JSON Schema in `schemas/workflow.schema.json` matching spec section 3.2
- [ ] **P1-2**: Define the action catalog JSON Schema in `schemas/action.schema.json` matching spec section 6
- [ ] **P1-3**: Define the API error JSON Schema in `schemas/api_error.schema.json` matching spec section 4.1 (422 response)
- [ ] **P1-4**: Create Pydantic request models in `src/api/models/requests.py` — `GenerateRequest` (description, output_format, strict_mode) and `ValidateRequest` (workflow definition body)
- [ ] **P1-5**: Create Pydantic response models in `src/api/models/responses.py` — `WorkflowDefinition`, `ValidationResult`, `AmbiguityError` with all nested types (Trigger, Step, Parameter, ErrorHandling)
- [ ] **P1-6**: Write the action catalog YAML format and create the first action definition: `fetch_data.yaml` with action_id, aliases, required_inputs, outputs, service
- [ ] **P1-7**: Create remaining starter action definitions: `transform_data.yaml`, `send_email.yaml`, `send_notification.yaml`, `write_file.yaml`, `http_request.yaml`
- [ ] **P1-8**: Build `src/catalog/registry.py` — load all YAML files from `src/catalog/actions/`, index by action_id, and provide a `lookup(phrase: str) -> Action | None` method that matches against aliases
- [ ] **P1-9**: Write `tests/unit/test_catalog.py` — test loading, lookup by exact alias, lookup by close match, and lookup miss

### Phase 2 — Parser and Analyzer

- [ ] **P2-1**: Write the system prompt in `src/prompts/system_prompt.txt` — instruct the LLM to act as a workflow extraction engine, returning structured JSON with actions, entities, temporal cues, conditions, and parameters
- [ ] **P2-2**: Write the extraction prompt template in `src/prompts/extraction_prompt.txt` — takes the user's description as input, returns the parsed extraction object
- [ ] **P2-3**: Write the disambiguation prompt in `src/prompts/disambiguation_prompt.txt` — takes ambiguous fragments and returns interpretations with confidence scores
- [ ] **P2-4**: Implement `src/pipeline/parser.py` — call the Claude API with the system + extraction prompts, parse the LLM response into a typed `ParseResult` dataclass containing: actions (verb + object), entities, temporal_cues, conditions, raw_parameters
- [ ] **P2-5**: Write `tests/unit/test_parser.py` — mock the Claude API response; test that a known input produces the expected `ParseResult` structure; test malformed LLM responses are handled gracefully
- [ ] **P2-6**: Implement `src/pipeline/analyzer.py` — take `ParseResult`, resolve each action against the catalog via `registry.lookup()`, resolve entity references across steps (e.g. "the report" → output of a prior step), detect implicit ordering, flag ambiguities, record assumptions
- [ ] **P2-7**: Write `tests/unit/test_analyzer.py` — test action alias resolution, entity cross-referencing, ambiguity detection in strict vs. non-strict mode, and assumption recording
- [ ] **P2-8**: Create the first example pair: write `examples/inputs/simple_report.txt` ("Every Monday morning, pull the latest sales data from our CRM, summarize it, and email the report to the team") and hand-craft the expected `examples/outputs/simple_report.json`

### Phase 3 — Graph and Planner

- [ ] **P3-1**: Implement `src/graph/dag.py` — DAG class with `add_node(id, metadata)`, `add_edge(from, to, condition?)`, `get_dependencies(id)`, `has_cycle()` methods
- [ ] **P3-2**: Implement `src/graph/topological.py` — `topological_sort(dag) -> list[str]` using Kahn's algorithm; raise on cycle detection
- [ ] **P3-3**: Write `tests/unit/test_dag.py` — test node/edge operations, cycle detection, topological sort on linear chains, fan-out, fan-in, and conditional edges
- [ ] **P3-4**: Implement `src/pipeline/planner.py` — take the Analyzer output, build a DAG of steps, assign trigger type from temporal cues (cron expression for schedules, event type for webhooks, manual as fallback), extract parameters from raw values, attach default error handling config
- [ ] **P3-5**: Write `tests/unit/test_planner.py` — test DAG construction from analyzed actions, trigger assignment for schedule/event/manual cases, parameter extraction, and error handling defaults

### Phase 4 — Serializer and API Endpoints

- [ ] **P4-1**: Implement `src/pipeline/serializer.py` — take the DAG + planner metadata, walk in topological order, produce the workflow definition dict, validate against `schemas/workflow.schema.json`, serialize to JSON or YAML based on requested format
- [ ] **P4-2**: Write `tests/unit/test_serializer.py` — test JSON output, YAML output, schema validation pass, and schema validation rejection for malformed workflows
- [ ] **P4-3**: Implement `src/pipeline/__init__.py` — `generate_workflow(description, output_format, strict_mode) -> WorkflowDefinition` that chains parser → analyzer → planner → serializer, catching and wrapping errors at each stage
- [ ] **P4-4**: Implement `POST /workflows/generate` in `src/api/routes/generate.py` — accept `GenerateRequest`, call `generate_workflow`, return `WorkflowDefinition` or `AmbiguityError` (422) or structured error (500)
- [ ] **P4-5**: Implement `POST /workflows/validate` in `src/api/routes/validate.py` — accept a workflow definition body, validate against JSON Schema, return `ValidationResult` with `valid: true` or `valid: false` with error paths
- [ ] **P4-6**: Register both route modules in `src/api/server.py`
- [ ] **P4-7**: Write `tests/integration/test_api.py` — test both endpoints via `httpx.AsyncClient`: successful generation, strict mode rejection, validation pass, validation failure
- [ ] **P4-8**: Write `tests/integration/test_pipeline.py` — end-to-end test from a real NL description through the full pipeline (with a live or mocked Claude API call) asserting the output has correct structure, trigger, and step count

### Phase 5 — Golden Tests, Remaining Examples, and Polish

- [ ] **P5-1**: Create remaining example inputs: `conditional_alert.txt`, `multi_step_pipeline.txt`, `webhook_trigger.txt`, `parameterized_etl.txt`
- [ ] **P5-2**: Hand-craft expected outputs for each: `conditional_alert.json`, `multi_step_pipeline.json`, `webhook_trigger.json`, `parameterized_etl.json`
- [ ] **P5-3**: Implement `tests/golden/test_golden.py` — discover all `examples/inputs/*.txt`, run each through the pipeline, compare output against the matching `examples/outputs/*.json`, report diffs
- [ ] **P5-4**: Add structured logging to the pipeline — log entry/exit of each stage with timing, log assumptions made, log ambiguities detected
- [ ] **P5-5**: Add request-level error handling middleware in `src/api/server.py` — catch unhandled exceptions, return structured JSON errors (never stack traces)
- [ ] **P5-6**: Add a `--dry-run` CLI entrypoint that reads a text file and prints the generated workflow to stdout (useful for local development without starting the server)
- [ ] **P5-7**: Review all action catalog entries against the golden test inputs — add any missing aliases surfaced during testing
- [ ] **P5-8**: Final pass — run full test suite, fix failures, verify all schemas are in sync with Pydantic models

### Phase 6 — Web UI and Export

- [x] **P6-1**: Create `POST /workflows/generate-steps` endpoint that returns intermediate results from each pipeline stage (parser, analyzer, planner, serializer) with timing and status
- [x] **P6-2**: Build single-page web UI in `ui/index.html` — text area input, pipeline stage visualization with expand/collapse, summary cards, JSON output viewer
- [x] **P6-3**: Add n8n format conversion in the UI — client-side mapping from LastautAI workflow schema to n8n node types and connections
- [x] **P6-4**: Add example input chips for quick experimentation with common workflow patterns
- [x] **P6-5**: Serve the UI at `GET /` from FastAPI, add CORS middleware
- [x] **P6-6**: Add copy-to-clipboard and download-as-file functionality for workflow output
- [ ] **P6-7**: Add YAML output tab alongside JSON and n8n formats
- [ ] **P6-8**: Add Make (Integromat) format conversion alongside n8n
- [x] **P6-9**: Update `docs/vision.md`, `docs/spec.md`, and `docs/backlog.md` to document the web UI

### Phase 7 — User Accounts, Database, and Dashboard

- [ ] **P7-1**: Add `sqlalchemy`, `passlib[bcrypt]`, `python-jose[cryptography]` to `pyproject.toml`
- [ ] **P7-2**: Create `src/db/database.py` — SQLAlchemy engine pointing at `data/lastautai.db`, session factory, `init_db()` that creates tables on startup
- [ ] **P7-3**: Create `src/db/models.py` — `User` model (id, username, email, password_hash, created_at) and `Workflow` model (id, user_id FK, name, description, workflow_json, n8n_id, created_at)
- [ ] **P7-4**: Create `src/auth/hashing.py` — bcrypt hash and verify functions via passlib
- [ ] **P7-5**: Create `src/auth/jwt.py` — create_token(user_id) and decode_token(token) using python-jose, signing with `AUTH_SECRET` env var, 24h expiry
- [ ] **P7-6**: Create `src/auth/dependencies.py` — FastAPI `Depends` function `get_current_user` that extracts and validates the JWT from the Authorization header
- [ ] **P7-7**: Create `POST /auth/signup` route — validate input, hash password, insert user, return JWT
- [ ] **P7-8**: Create `POST /auth/login` route — verify credentials, return JWT
- [ ] **P7-9**: Create `GET /auth/me` route — return current user info (requires auth)
- [ ] **P7-10**: Create `GET /workflows/history` route — return list of user's saved workflows (requires auth)
- [ ] **P7-11**: Create `GET /workflows/{id}` route — return a specific saved workflow (requires auth, must belong to user)
- [ ] **P7-12**: Update `POST /workflows/generate-steps` to save the generated workflow to the database when a user is authenticated
- [ ] **P7-13**: Update `POST /n8n/deploy` to record the n8n workflow ID on the saved workflow record
- [ ] **P7-14**: Update UI — add login/signup screens, persist JWT in localStorage, send Authorization header on API calls
- [ ] **P7-15**: Update UI — add dashboard layout with tabs: Record (placeholder), Suggested Workflows (placeholder), Create Workflow (existing), My Workflows (history list)
- [ ] **P7-16**: Update UI — My Workflows tab shows list of past workflows with name, date, re-export and re-deploy actions
- [ ] **P7-17**: Add `data/` to `.gitignore` so the SQLite database is never committed
- [x] **P7-18**: Update `docs/vision.md`, `docs/spec.md`, and `docs/backlog.md` to document user accounts and dashboard
