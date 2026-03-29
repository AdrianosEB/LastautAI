# Desktop Activity Monitor — Design

## Important: How This Runs
Because screen recording needs access to the local machine, **Django must run locally** (`python manage.py runserver`), not on PythonAnywhere. The user opens `localhost:8000` in their browser. The recording happens server-side, which in this case IS their own machine.

> No Claude Desktop API is needed. We use Python libraries to capture events locally, and the Claude text API to analyze and describe the patterns.

---

## Stack
| Layer | Tool |
|-------|------|
| Frontend | HTML/CSS/JS (Django templates) |
| Backend | Django (Python) |
| Event capture | `pynput` (mouse/keyboard), `subprocess` (active app via AppleScript on macOS) |
| Pattern analysis | Claude API (`claude-opus-4-6`) |
| Storage | SQLite via Django models |

---

## System Flow
```
User clicks "Start Recording" in browser
        ↓
Django starts a background thread (ScreenRecorder)
        ↓
Every event (click, app switch) → added to an in-memory buffer
        ↓
Every 5 minutes → buffer is flushed and sent to Claude API
        ↓
Claude returns a plain-language workflow description
        ↓
Saved to DB → shown on dashboard as a suggestion
        ↓
User reviews → passes to automation layer (Person 2)
```

---

## Django MVC Structure

```
capture/
  models.py     ← EventLog, WorkflowSuggestion
  views.py      ← start/stop recording, fetch suggestions
  recorder.py   ← background thread, event capture logic
  analyzer.py   ← sends buffered events to Claude API
  urls.py
templates/capture/
  monitor.html  ← dashboard with Start/Stop button + suggestions panel
```

---

## Models

```python
# EventLog — one row per captured event
class EventLog(models.Model):
    user         = ForeignKey(User)
    timestamp    = DateTimeField(auto_now_add=True)
    event_type   = CharField()   # "click", "app_switch", "key_sequence"
    app_name     = CharField()   # e.g. "Google Chrome"
    window_title = CharField()   # e.g. "Inbox - Outlook"
    detail       = CharField()   # e.g. coordinates, menu path

# WorkflowSuggestion — Claude's output after analyzing a batch of events
class WorkflowSuggestion(models.Model):
    user        = ForeignKey(User)
    created_at  = DateTimeField(auto_now_add=True)
    description = TextField()    # plain-language workflow summary
    raw_events  = TextField()    # the event batch that produced this
    status      = CharField()    # "pending", "approved", "dismissed"
```

---

## What Gets Captured Per Event

| Field | Example |
|-------|---------|
| `event_type` | `app_switch` |
| `app_name` | `Finder` |
| `window_title` | `Downloads` |
| `detail` | `opened folder: Reports` |
| `timestamp` | `09:04:32` |

Passwords and message content are never captured. Only app names, window titles, and click coordinates.

**Active app detection (macOS):**
```python
import subprocess
result = subprocess.run(
    ['osascript', '-e',
     'tell application "System Events" to get name of first process whose frontmost is true'],
    capture_output=True, text=True
)
app_name = result.stdout.strip()
```

---

## Periodic Analysis (every 5 minutes)

The buffer of recent events is formatted into a readable log and sent to Claude:

```
Prompt to Claude:
"Here is a log of the user's recent activity. Identify any repeated
sequences, common workflows, or patterns that could be automated.
Write a short plain-language description of each pattern you find."

Event log:
09:01 — opened Chrome → Gmail
09:02 — clicked attachment → downloaded file
09:03 — opened Finder → moved file to /Reports
09:04 — returned to Gmail → repeated
...
```

Claude returns something like:
> "You repeatedly open Gmail, download an attachment, and move it to your Reports folder. This happened 4 times in this session and appears to be a daily routine."

---

## Frontend — monitor.html

```
+-----------------------------------------------+
|  Activity Monitor                   [Logged in]|
+-----------------------------------------------+
|  [  Start Recording  ]   Status: Idle          |
|                                                |
|  Suggestions                                   |
|  ┌─────────────────────────────────────────┐   |
|  │ "You open Gmail and move attachments    │   |
|  │  to Reports every morning."             │   |
|  │  [Send to Automation]  [Dismiss]        │   |
|  └─────────────────────────────────────────┘   |
+-----------------------------------------------+
```

- Start/Stop triggers a POST to `/capture/start/` or `/capture/stop/`
- Suggestions poll `/capture/suggestions/` every 30 seconds
- "Send to Automation" passes the description to Person 2's workflow layer

---

## Handoff to Automation Layer

When a suggestion is approved, the `WorkflowSuggestion.description` is passed as input to the agent workflow designed by Person 2. This is the text output described in the vision doc.
