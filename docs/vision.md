# Vision: Natural Language to Workflow Automation

## Problem Statement

Building automations today requires technical knowledge of specific platforms, APIs, and scripting languages. Users who understand *what* they want automated are blocked by *how* to express it in a form machines can execute. This gap between intent and implementation slows down teams, creates bottlenecks on engineering resources, and leaves countless repetitive tasks unautomated.

## Vision

A system where anyone can describe a task in plain language and receive a structured, executable workflow definition in return — no coding required, no platform-specific syntax to learn.

> "Every Monday morning, pull the latest sales data from our CRM, summarize it, and email the report to the team."

That sentence becomes a fully defined workflow: trigger, steps, inputs, outputs, error handling — ready to plug into a workflow engine and run.

## Core Capabilities

### 1. Intent Extraction
Understand *what* the user wants to achieve, not just the literal words they used. Distinguish between the goal ("keep the team informed on sales") and the mechanism ("pull data, summarize, email").

### 2. Step Decomposition
Break a natural language description into discrete, ordered actions. Each step has a clear action, defined inputs and outputs, and identified external services or tools.

### 3. Control Flow Detection
Recognize conditional logic, loops, branching, parallelism, and error handling embedded in everyday language. Phrases like "if the total exceeds $10k, also notify the manager" map to conditional branches in the workflow.

### 4. Trigger Identification
Determine what kicks off the workflow — a schedule (cron), an event (webhook, file upload, database change), or a manual trigger — based on temporal and contextual cues in the description.

### 5. Parameter Extraction
Surface configurable values (thresholds, recipients, file paths, time intervals) as named, typed parameters with sensible defaults, so workflows are reusable without editing their definitions.

## Output

A structured workflow definition (JSON or YAML) containing:

| Field            | Description                                                        |
|------------------|--------------------------------------------------------------------|
| `name`           | Concise title for the workflow                                     |
| `trigger`        | What starts the workflow and its configuration                     |
| `steps`          | Ordered list of actions with IDs, inputs, outputs, and dependencies|
| `parameters`     | User-configurable variables with types and defaults                |
| `error_handling` | Retry policies and failure behavior at workflow and step level     |

## Design Principles

- **Fidelity to intent** — Never add steps or logic the user did not describe. The system automates what was asked, nothing more.
- **Transparency over magic** — When the description is ambiguous, surface assumptions explicitly rather than guessing silently.
- **Structured and portable** — Output is valid, parseable structured data that can serve as input for any workflow engine or code generator.
- **Parameterize, don't hard-code** — Configurable values are extracted as parameters so workflows are adaptable without modification.

## Target Users

- Business teams who know their processes but lack engineering resources to automate them.
- Developers who want to rapidly prototype automations from high-level descriptions.
- Operations and support staff looking to codify repetitive manual workflows.

## Web Interface

The system includes a browser-based UI that makes the NL-to-workflow pipeline accessible and transparent:

### Step-by-Step Pipeline Visualization
Users see each processing stage (Parser, Analyzer, Planner, Serializer) execute in real time with status indicators, timing, and expandable intermediate results. This transparency builds trust — users understand *how* their words became a workflow, not just the final output.

### Input Experience
- Large text area for entering workflow descriptions in plain language
- Pre-built example chips for quick experimentation
- Keyboard shortcut (Cmd/Ctrl+Enter) for fast generation

### Output & Export
- Summary cards showing trigger type, step count, and parameter count at a glance
- Full workflow JSON with syntax highlighting
- **n8n-compatible export** — one-click conversion to n8n's workflow format, ready to import directly
- Copy-to-clipboard and download buttons for immediate use in any automation platform

### Design Principles for the UI
- **Show the work** — Every pipeline stage is visible and inspectable, reinforcing the "transparency over magic" principle
- **Export-ready** — Output is not just viewable but immediately actionable in real automation tools
- **Zero setup** — The UI is served directly by the FastAPI backend at `/`, no separate frontend build required

## User Accounts and Workflow History

The system supports individual user accounts so that each person's workflows are saved, retrievable, and tied to their identity.

### Authentication
- Users sign up with username, email, and password
- Passwords are hashed with bcrypt — never stored in plaintext
- Sessions are managed via JWT tokens stored in the browser
- All workflow endpoints require authentication

### Per-User Workflow Storage
- Every generated workflow is saved to the user's account automatically
- Users can view, re-export, or re-deploy any past workflow from their dashboard
- Workflow history includes the original natural language description, the generated JSON, and any n8n deployment IDs

### Dashboard Experience
The authenticated user lands on a dashboard with three sections:

1. **Record** — (future) Record actions to auto-generate workflows from observed behavior
2. **Suggested Workflows** — (future) AI-suggested workflows based on usage patterns
3. **Create Workflow** — The existing type-in + generate + deploy flow

## Success Criteria

- A plain-language description produces a correct, complete workflow definition on the first attempt for common use cases.
- Ambiguities are flagged with clear assumptions, not silently resolved.
- Generated workflows are valid structured data that can be loaded by a workflow engine without manual editing.
- The web UI shows each pipeline stage and produces output that can be directly imported into n8n or similar tools.
- Users can sign up, log in, and access their previously generated workflows.
