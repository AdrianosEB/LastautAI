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

---

## Screen Recording Pattern Analysis

### Goal

Analyze a batch of captured desktop activity events and identify repeatable patterns that could be automated as workflows.

### Input

A timestamped log of user events captured over 1-5 minutes:

```
09:01:00 [app_switch] Chrome — Gmail
09:01:10 [click] Chrome (x=500 y=300)
09:01:20 [app_switch] Finder — Downloads
09:01:30 [click] Finder (/Users/me/Downloads)
09:01:40 [app_switch] Chrome — Gmail
09:01:50 [click] Chrome (x=500 y=300)
09:02:00 [app_switch] Finder — Downloads
```

### Processing Requirements

1. **Pattern detection** — Identify repeated sequences of actions (e.g., switching between the same apps in the same order).
2. **Frequency assessment** — Note how many times the pattern appears in the batch.
3. **Automation potential** — Judge whether the pattern looks like something that could be automated.

### Output Format

2-3 plain-language sentences describing:
- What the user is doing
- How often the pattern repeats
- Whether it could be automated

If no clear patterns exist, respond only with: "Not enough data to identify patterns yet."

### Constraints

- Keep responses concise and non-technical — the user is not a developer.
- Do not use bullet points.
- Do not invent actions the user did not perform.
- Model: Claude Haiku (fast, cheap — this runs every 60 seconds).