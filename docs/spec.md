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

## 10. Milestones

| Phase | Deliverable                                                        |
|-------|--------------------------------------------------------------------|
| 1     | Data models, API contracts, and action catalog schema defined      |
| 2     | Parser and Analyzer — extract intent and actions from plain text   |
| 3     | Planner — build step DAG with triggers, dependencies, parameters   |
| 4     | Serializer and API — end-to-end workflow generation via REST       |
| 5     | Validation endpoint, golden test suite, and documentation          |
| 6     | Web UI with step-by-step visualization and n8n export              |
