import time
import threading
import subprocess
import platform
from datetime import datetime

_recorders = {}   # user_id -> ScreenRecorder
_lock = threading.Lock()


# ── OS helpers ────────────────────────────────────────────────────────────────

def _get_active_app():
    """Return the name of the frontmost application (macOS only)."""
    if platform.system() != 'Darwin':
        return 'Unknown'
    try:
        result = subprocess.run(
            ['osascript', '-e',
             'tell application "System Events" to get name of '
             'first process whose frontmost is true'],
            capture_output=True, text=True, timeout=1
        )
        return result.stdout.strip() or 'Unknown'
    except Exception:
        return 'Unknown'


def _get_window_title():
    """Return the title of the focused window (macOS only)."""
    if platform.system() != 'Darwin':
        return ''
    try:
        script = '''
        tell application "System Events"
            set frontApp to name of first process whose frontmost is true
            tell process frontApp
                try
                    return name of front window
                on error
                    return ""
                end try
            end tell
        end tell
        '''
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True, text=True, timeout=2
        )
        return result.stdout.strip()
    except Exception:
        return ''


# ── Recorder thread ───────────────────────────────────────────────────────────

class ScreenRecorder(threading.Thread):
    ANALYSIS_INTERVAL = 30  # seconds between each analysis flush (set to 5*60 for production)

    def __init__(self, user_id):
        super().__init__(daemon=True)
        self.user_id = user_id
        self.running = False
        self.buffer = []
        self.last_app = None
        self.last_analysis_time = time.time()
        self._mouse_listener = None

    def run(self):
        from pynput import mouse
        self.running = True

        self._mouse_listener = mouse.Listener(on_click=self._on_click)
        self._mouse_listener.start()

        while self.running:
            self._check_app_switch()

            if self.buffer and (time.time() - self.last_analysis_time) >= self.ANALYSIS_INTERVAL:
                self._flush_and_analyze()

            time.sleep(1)

        if self._mouse_listener:
            self._mouse_listener.stop()

    def stop(self):
        self.running = False

    # ── event handlers ────────────────────────────────────────────────────────

    def _log(self, event_type, app_name, window_title='', detail=''):
        self.buffer.append({
            'timestamp':    datetime.now().strftime('%H:%M:%S'),
            'event_type':   event_type,
            'app_name':     app_name,
            'window_title': window_title,
            'detail':       detail,
        })

    def _on_click(self, x, y, button, pressed):
        if pressed:
            self._log('click', _get_active_app(), detail=f'x={x} y={y}')

    def _check_app_switch(self):
        app = _get_active_app()
        if app and app != self.last_app:
            self._log('app_switch', app, window_title=_get_window_title())
            self.last_app = app

    # ── flush + analyze ───────────────────────────────────────────────────────

    def _flush_and_analyze(self):
        from .models import EventLog, WorkflowSuggestion
        from .analyzer import analyze_events
        from django.contrib.auth.models import User

        snapshot = list(self.buffer)
        self.buffer = []
        self.last_analysis_time = time.time()

        if not snapshot:
            return

        try:
            user = User.objects.get(pk=self.user_id)

            EventLog.objects.bulk_create([
                EventLog(
                    user=user,
                    event_type=e['event_type'],
                    app_name=e['app_name'],
                    window_title=e['window_title'],
                    detail=e['detail'],
                )
                for e in snapshot
            ])

            description = analyze_events(snapshot)

            if description and 'not enough data' not in description.lower():
                raw = '\n'.join(
                    f"{e['timestamp']} [{e['event_type']}] {e['app_name']}"
                    + (f" — {e['window_title']}" if e['window_title'] else '')
                    + (f" ({e['detail']})" if e['detail'] else '')
                    for e in snapshot
                )
                WorkflowSuggestion.objects.create(
                    user=user,
                    description=description,
                    raw_events=raw,
                )
        except Exception as exc:
            print(f'[Recorder] Error during flush: {exc}')


# ── Public API ────────────────────────────────────────────────────────────────

def start(user_id):
    with _lock:
        r = _recorders.get(user_id)
        if r and r.is_alive():
            return False
        recorder = ScreenRecorder(user_id)
        _recorders[user_id] = recorder
        recorder.start()
        return True


def stop(user_id):
    with _lock:
        recorder = _recorders.pop(user_id, None)
    if recorder:
        recorder.stop()
        return True
    return False


def is_running(user_id):
    with _lock:
        r = _recorders.get(user_id)
        return r is not None and r.is_alive()
