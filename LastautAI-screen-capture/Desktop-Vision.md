# Desktop Activity Monitor — Vision

## What It Does
A desktop agent that watches how the user works (with their permission) and identifies repetitive patterns that could be automated. It runs quietly in the background and only acts when the user approves.

---

## Opt-In Flow
```
User installs agent
        ↓
Prompted: "Allow screen activity monitoring?" → Yes / No
        ↓
If Yes: monitoring begins passively
If No:  nothing runs, can enable later in settings
```

---

## What Gets Monitored
| Signal | Example |
|--------|---------|
| App focus & switching | Opens Outlook → Chrome → Excel every morning |
| File activity | Downloads attachments from email at 9am daily |
| Click sequences | Same series of menu clicks to export a report |
| Typing patterns | Fills the same form fields repeatedly |
| Time-of-day context | Certain workflows always happen at the same time |

We do **not** capture: passwords, private messages, or anything outside approved apps.

---

## Storage vs. Real-Time

**Option A — Store & Analyze**
- Log events locally on the user's machine
- Run pattern analysis on a schedule (e.g. end of day)
- Better for detecting patterns that span multiple sessions

**Option B — Real-Time**
- Analyze events as they happen
- Can surface suggestions mid-session
- Higher resource usage

**Plan:** Start with Option A (store locally, analyze periodically). Add real-time hints later.

---

## Data Flow
```
Screen activity
      ↓
Event logger (local, encrypted)
      ↓
Pattern analyzer (finds repeated sequences)
      ↓
Workflow description (what the user does, how often, what's automatable)
      ↓
Passed to automation layer (Person 2's workstream)
```

---

## Output
For each detected pattern, the system produces a plain-language workflow summary:

> "Every weekday morning, you open Outlook, download 2–3 attachments, and move them to the same folder. This happens ~5x per week and could be automated."

This summary is what gets handed off to the agent/workflow layer to design an automation.

---

## Key Principles
- **Opt-in only** — nothing runs without explicit user consent
- **Local first** — data stays on the user's machine
- **Transparent** — user can see exactly what's being logged
- **Non-intrusive** — suggestions appear only when there's something worth showing
