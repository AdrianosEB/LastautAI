"""
Screen recorder thread — captures mouse clicks and app switches.
Ported from LastautAI-screen-capture/capture/recorder.py, adapted for SQLAlchemy.
"""

import logging
import time
import threading
import subprocess
import platform
from datetime import datetime

logger = logging.getLogger(__name__)

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


def _get_app_detail(app_name):
    """Return richer context for specific apps (URL for browsers, path for Finder)."""
    if platform.system() != 'Darwin':
        return ''
    try:
        if app_name in ('Google Chrome', 'Chromium'):
            script = 'tell application "Google Chrome" to get URL of active tab of first window'
        elif app_name == 'Safari':
            script = 'tell application "Safari" to get URL of current tab of first window'
        elif app_name == 'Firefox':
            script = '''tell application "System Events" to tell process "Firefox"
                try
                    return name of front window
                on error
                    return ""
                end try
            end tell'''
        elif app_name == 'Finder':
            script = '''tell application "Finder"
                try
                    return POSIX path of (target of front window as alias)
                on error
                    return ""
                end try
            end tell'''
        else:
            return ''

        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True, text=True, timeout=2
        )
        return result.stdout.strip()
    except Exception:
        return ''


# ── Recorder thread ───────────────────────────────────────────────────────────

class ScreenRecorder(threading.Thread):
    ANALYSIS_INTERVAL = 60  # seconds between each analysis flush

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
        # Wait for the thread to finish its current loop iteration
        self.join(timeout=5)
        # Flush any remaining events so short recordings still produce suggestions
        if self.buffer:
            self._flush_and_analyze()

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
            app = _get_active_app()
            detail = _get_app_detail(app) or f'x={x} y={y}'
            self._log('click', app, window_title=_get_window_title(), detail=detail)

    def _check_app_switch(self):
        app = _get_active_app()
        if app and app != self.last_app:
            detail = _get_app_detail(app)
            self._log('app_switch', app, window_title=_get_window_title(), detail=detail)
            self.last_app = app

    # ── flush + analyze ───────────────────────────────────────────────────────

    def _flush_and_analyze(self):
        from src.db.database import SessionLocal
        from src.db.models import EventLog, WorkflowSuggestion
        from src.capture.analyzer import analyze_events

        snapshot = list(self.buffer)
        self.buffer = []
        self.last_analysis_time = time.time()

        if not snapshot:
            return

        db = SessionLocal()
        try:
            # Save events to DB
            for e in snapshot:
                db.add(EventLog(
                    user_id=self.user_id,
                    event_type=e['event_type'],
                    app_name=e['app_name'],
                    window_title=e['window_title'],
                    detail=e['detail'],
                ))
            db.commit()

            # Analyze with Claude
            description = analyze_events(snapshot)
            logger.info('Analyzer response: %s', description[:100])

            if description:
                raw = '\n'.join(
                    f"{e['timestamp']} [{e['event_type']}] {e['app_name']}"
                    + (f" — {e['window_title']}" if e['window_title'] else '')
                    + (f" ({e['detail']})" if e['detail'] else '')
                    for e in snapshot
                )
                # Generate a clean summary immediately
                summary = ''
                try:
                    from src.capture.analyzer import summarize_suggestion
                    summary = summarize_suggestion(description)
                except Exception as exc:
                    logger.warning('Summary error: %s', exc)

                db.add(WorkflowSuggestion(
                    user_id=self.user_id,
                    description=description,
                    summary=summary,
                    raw_events=raw,
                ))
                db.commit()
                logger.info('Saved suggestion for user %s: %s', self.user_id, summary or description[:60])
            else:
                logger.info('Skipped saving — response filtered out')
        except Exception as exc:
            logger.error('Error during flush: %s', exc, exc_info=True)
            db.rollback()
        finally:
            db.close()


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
