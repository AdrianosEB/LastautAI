## Natural Language to Workflow Automation

### Goal

Build a system that converts plain-language descriptions of tasks, behaviors, or workflows into structured, executable automation definitions.

### Input

A free-form natural language description of what the user wants to automate (e.g. "Every Monday morning, pull the latest sales data from our CRM, summarize it, and email the report to the team").

### Processing Requirements

1. **Intent extraction** — Determine the core goal and desired outcome of the described task.
2. **Step decomposition** — Break the description into discrete, ordered actions. For each step, identify:
   - The action to perform (e.g. fetch data, transform, send notification)
   - Required inputs and expected outputs
   - External services or tools involved
3. **Control flow detection** — Recognize conditions, loops, branching logic, error handling, and parallel paths implied by the language (e.g. "if the total exceeds $10k, also notify the manager").
4. **Trigger identification** — Determine what initiates the workflow: a schedule, an event, a manual trigger, or a webhook.
5. **Variable and parameter extraction** — Surface any configurable values (thresholds, recipients, file paths) so they can be parameterized rather than hard-coded.

### Output Format

Return a structured workflow definition containing:

- **name** — A concise, descriptive title for the workflow.
- **trigger** — What starts the workflow and its configuration (cron expression, event type, etc.).
- **steps** — An ordered list where each step includes:
  - `id` — Unique step identifier.
  - `action` — What the step does.
  - `inputs` — Data or parameters the step consumes.
  - `outputs` — Data the step produces for downstream steps.
  - `dependencies` — IDs of steps that must complete first.
  - `conditions` (optional) — Logic that determines whether the step runs.
- **parameters** — User-configurable variables with names, types, defaults, and descriptions.
- **error_handling** — Default retry and failure behavior for the workflow and any step-level overrides.

### Constraints

- Preserve the user's original intent — do not add steps or logic the user did not describe.
- When the description is ambiguous, note assumptions explicitly rather than guessing silently.
- The output must be valid, parseable structured data (JSON or YAML) ready to serve as input for a workflow engine or code generator.