# Testing Plan — Desktop Activity Monitor

## Philosophy

Tests call functions directly with simulated inputs — no sleeping, no clicking around, no waiting for timers. Each test targets one layer of the pipeline.

---

## Test 1: Event logging (recorder buffer)

Directly call `_on_click` and `_check_app_switch` on a recorder instance without starting the thread. Check that events land in the buffer correctly.

```python 
# python manage.py shell 
from capture.recorder import ScreenRecorder

r = ScreenRecorder(user_id=1)

# Simulate an app switch
r._check_app_switch.__func__(r)   # or just set last_app manually and call _log
r.last_app = "Finder"
r._log('app_switch', 'Chrome', window_title='Gmail')
r._log('click', 'Chrome', detail='x=100 y=200')
r._log('app_switch', 'Finder', window_title='Downloads')

print(r.buffer)
# Expected: 3 dicts with correct event_type, app_name, etc.
```

**Pass:** buffer has 3 events with the right fields
**Fail:** KeyError or missing fields → check `_log()` in recorder.py

---

## Test 2: Analyzer (Gemini API call)

Call `analyze_events` directly with fake pre-built events. No recorder thread, no timer.

```python
from capture.analyzer import analyze_events

fake_events = [
    {'timestamp': '09:01:00', 'event_type': 'app_switch', 'app_name': 'Chrome',  'window_title': 'Gmail',      'detail': ''},
    {'timestamp': '09:01:10', 'event_type': 'click',      'app_name': 'Chrome',  'window_title': '',           'detail': 'x=500 y=300'},
    {'timestamp': '09:01:20', 'event_type': 'app_switch', 'app_name': 'Finder',  'window_title': 'Downloads',  'detail': ''},
    {'timestamp': '09:01:30', 'event_type': 'click',      'app_name': 'Finder',  'window_title': '',           'detail': 'x=200 y=400'},
    {'timestamp': '09:01:40', 'event_type': 'app_switch', 'app_name': 'Chrome',  'window_title': 'Gmail',      'detail': ''},
    {'timestamp': '09:01:50', 'event_type': 'click',      'app_name': 'Chrome',  'window_title': '',           'detail': 'x=500 y=300'},
    {'timestamp': '09:02:00', 'event_type': 'app_switch', 'app_name': 'Finder',  'window_title': 'Downloads',  'detail': ''},
]

result = analyze_events(fake_events)
print(result)
```

**Pass:** Gemini returns a plain-language description (or "Not enough data...")
**Fail:** `KeyError: GEMINI_API_KEY` → run `export GEMINI_API_KEY=...` first

---

## Test 3: Flush writes to the database

Pre-load the buffer with fake events and call `_flush_and_analyze()` directly. Skips the timer entirely.

```python
from capture.recorder import ScreenRecorder
from capture.models import EventLog, WorkflowSuggestion

r = ScreenRecorder(user_id=1)

# Inject fake events straight into the buffer
r.buffer = [
    {'timestamp': '09:01:00', 'event_type': 'app_switch', 'app_name': 'Chrome',  'window_title': 'Gmail',     'detail': ''},
    {'timestamp': '09:01:10', 'event_type': 'click',      'app_name': 'Chrome',  'window_title': '',          'detail': 'x=500 y=300'},
    {'timestamp': '09:01:20', 'event_type': 'app_switch', 'app_name': 'Finder',  'window_title': 'Downloads', 'detail': ''},
    {'timestamp': '09:01:30', 'event_type': 'app_switch', 'app_name': 'Chrome',  'window_title': 'Gmail',     'detail': ''},
    {'timestamp': '09:01:40', 'event_type': 'click',      'app_name': 'Chrome',  'window_title': '',          'detail': 'x=500 y=300'},
    {'timestamp': '09:01:50', 'event_type': 'app_switch', 'app_name': 'Finder',  'window_title': 'Downloads', 'detail': ''},
]

before_events      = EventLog.objects.count()
before_suggestions = WorkflowSuggestion.objects.count()

r._flush_and_analyze()

print("EventLogs added:",      EventLog.objects.count()          - before_events)
print("Suggestions added:",    WorkflowSuggestion.objects.count() - before_suggestions)
print("Latest suggestion:",    WorkflowSuggestion.objects.last())
```

**Pass:** EventLog count increases by 6; a suggestion is created (or "Not enough data" is returned and no suggestion row is added — both are correct)
**Fail:** exception printed → check console output for the error message

---

## Test 4: API endpoints (Django views)

Use Django's test client to hit start/stop/suggestions without a real browser.

```python
from django.test import Client
from django.contrib.auth.models import User

# Create a test user if needed
user, _ = User.objects.get_or_create(username='testuser')
user.set_password('pass')
user.save()

c = Client()
c.login(username='testuser', password='pass')

# Start recording
r = c.post('/capture/start/')
print(r.json())   # {"status": "started"}

# Stop recording
r = c.post('/capture/stop/')
print(r.json())   # {"status": "stopped"}

# Get suggestions (should be empty list initially)
r = c.get('/capture/suggestions/')
print(r.json())   # {"suggestions": [...]}
```

**Pass:** all three return the expected JSON with correct status codes
**Fail:** 302 redirect → not logged in; 404 → URL not registered in urls.py

---

## Test 5: End-to-end (full pipeline, no waiting)

Combines Tests 3 + 4: inject events, flush, then verify the suggestion appears via the API.

```python
from django.test import Client
from django.contrib.auth.models import User
from capture.recorder import ScreenRecorder
from capture.models import WorkflowSuggestion

user, _ = User.objects.get_or_create(username='testuser')
user.set_password('pass')
user.save()

# Inject and flush
r = ScreenRecorder(user_id=user.id)
r.buffer = [
    {'timestamp': '09:01:00', 'event_type': 'app_switch', 'app_name': 'Chrome', 'window_title': 'Gmail',     'detail': ''},
    {'timestamp': '09:01:10', 'event_type': 'click',      'app_name': 'Chrome', 'window_title': '',          'detail': 'x=500 y=300'},
    {'timestamp': '09:01:20', 'event_type': 'app_switch', 'app_name': 'Finder', 'window_title': 'Downloads', 'detail': ''},
    {'timestamp': '09:01:30', 'event_type': 'app_switch', 'app_name': 'Chrome', 'window_title': 'Gmail',     'detail': ''},
    {'timestamp': '09:01:40', 'event_type': 'click',      'app_name': 'Chrome', 'window_title': '',          'detail': 'x=500 y=300'},
    {'timestamp': '09:01:50', 'event_type': 'app_switch', 'app_name': 'Finder', 'window_title': 'Downloads', 'detail': ''},
]
r._flush_and_analyze()

# Verify it shows up via the API
c = Client()
c.login(username='testuser', password='pass')
resp = c.get('/capture/suggestions/')
suggestions = resp.json()['suggestions']
print(f"Suggestions on dashboard: {len(suggestions)}")
if suggestions:
    print(suggestions[0]['description'])
```

**Pass:** at least one suggestion appears with a description
**Fail:** empty list → flush may have returned "Not enough data", check `WorkflowSuggestion.objects.last()`

---

## Summary

| Test | What it checks | User action needed? |
|------|---------------|---------------------|
| 1 — Buffer | Events logged correctly | None — calls `_log()` directly |
| 2 — Analyzer | Gemini API works | None — fake events passed in |
| 3 — Flush | DB writes work | None — buffer pre-loaded |
| 4 — Endpoints | Views return correct JSON | None — Django test client |
| 5 — End-to-end | Full pipeline | None — all simulated |
