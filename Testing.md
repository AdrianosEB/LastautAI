# Testing Plan — Desktop Activity Monitor

## Why "Nothing Seems to Happen"

The recorder only saves events to the database **after a 5-minute timer fires** (`ANALYSIS_INTERVAL = 5 * 60`). So clicking Start and waiting 30 seconds will show nothing — that's expected. Also, macOS may block the AppleScript calls if **Accessibility permissions** haven't been granted to the Terminal or browser running Django.

---

## Layer-by-Layer Tests (run in order)

### 1. Permissions check (macOS)
Before anything else, confirm macOS is allowing event capture:

```bash
# In a Python shell, try getting the active app
python3 -c "
import subprocess
r = subprocess.run(['osascript', '-e', 'tell application \"System Events\" to get name of first process whose frontmost is true'], capture_output=True, text=True)
print('App:', r.stdout.strip(), '| Error:', r.stderr.strip())
"
```
**Pass:** prints the current app name (e.g. `Terminal`)
**Fail:** empty output or permission error → go to System Settings → Privacy & Security → Accessibility → add Terminal

---

### 2. Recorder thread (does start/stop actually work?)

```bash
python manage.py shell
```
```python
from capture import recorder as rec

rec.start(1)              # use your user ID
import time; time.sleep(3)
print(rec.is_running(1))  # should print True

rec.stop(1)
print(rec.is_running(1))  # should print False
```
**Pass:** True then False
**Fail:** error on start → likely a `pynput` import issue, run `pip install pynput`

---

### 3. Event capture (are events going into the buffer?)

```python
from capture import recorder as rec
import time

rec.start(1)
time.sleep(5)  # click around and switch apps during this time

r = rec._recorders.get(1)
print(f"Buffer has {len(r.buffer)} events")
print(r.buffer[:3])

rec.stop(1)
```
**Pass:** buffer has events matching your clicks/app switches
**Fail:** buffer is empty → AppleScript or pynput permissions not granted

---

### 4. Force an early flush (bypass the 5-min wait)

```python
from capture import recorder as rec
import time

rec.start(1)
time.sleep(10)  # click around

r = rec._recorders.get(1)
print("Buffer before flush:", len(r.buffer))
r._flush_and_analyze()  # call it directly, skips the timer
print("Buffer after flush:", len(r.buffer))

rec.stop(1)
```
Then check the database:
```python
from capture.models import EventLog, WorkflowSuggestion
print(EventLog.objects.count())
print(WorkflowSuggestion.objects.last())
```
**Pass:** EventLog count increases; WorkflowSuggestion is created (or "Not enough data" is returned)
**Fail:** exception printed → check the console output for the error

---

### 5. Analyzer (Claude API call in isolation)

```python
from capture.analyzer import analyze_events

fake_events = [
    {'timestamp': '09:01:00', 'event_type': 'app_switch', 'app_name': 'Chrome', 'window_title': 'Gmail', 'detail': ''},
    {'timestamp': '09:01:10', 'event_type': 'click',      'app_name': 'Chrome', 'window_title': '',      'detail': 'x=500 y=300'},
    {'timestamp': '09:01:20', 'event_type': 'app_switch', 'app_name': 'Finder', 'window_title': 'Downloads', 'detail': ''},
    {'timestamp': '09:01:30', 'event_type': 'app_switch', 'app_name': 'Chrome', 'window_title': 'Gmail', 'detail': ''},
]

result = analyze_events(fake_events)
print(result)
```
**Pass:** Claude returns a plain-language description
**Fail:** `AuthenticationError` → `ANTHROPIC_API_KEY` env var is not set

---

### 6. API endpoints (does the frontend talk to Django correctly?)

With the server running (`python manage.py runserver`), open a second terminal:

```bash
# Get a CSRF token and session cookie first by logging in via browser,
# then use curl or the browser console:

# In the browser console (after logging in):
fetch('/capture/start/', {method: 'POST', headers: {'X-CSRFToken': document.cookie.match(/csrftoken=([^;]+)/)[1]}})
  .then(r => r.json()).then(console.log)
# Expected: {"status": "started"}

fetch('/capture/suggestions/')
  .then(r => r.json()).then(console.log)
# Expected: {"suggestions": [...]}
```

---

## End-to-End Quick Test

To do a full test without waiting 5 minutes, **temporarily lower the interval**:

In `capture/recorder.py`, line 58 — change:
```python
ANALYSIS_INTERVAL = 5 * 60  # original
```
to:
```python
ANALYSIS_INTERVAL = 30  # 30 seconds for testing
```

Then:
1. Start the server and log in
2. Click Start Recording
3. Switch between a few apps and click around for 30 seconds
4. Wait — a suggestion should appear on the dashboard automatically (the page polls every 30s)

**Remember to revert `ANALYSIS_INTERVAL` back to `5 * 60` after testing.**

---

## Summary Table

| Test | What it checks | Expected result |
|------|---------------|-----------------|
| Permissions | macOS AppleScript access | Active app name printed |
| Thread start/stop | `recorder.start()` / `stop()` | `is_running` toggles correctly |
| Buffer fill | Events being captured | Buffer grows as you use the computer |
| Force flush | DB write + Claude call | EventLog rows added, suggestion created |
| Analyzer alone | Claude API key + network | Plain-language description returned |
| API endpoints | Frontend ↔ Django | JSON responses with correct status |
| End-to-end (30s) | Full pipeline | Suggestion appears on dashboard |
