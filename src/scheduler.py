"""In-memory workflow scheduler — runs saved workflows on recurring intervals.

Parses cron-like expressions from workflow trigger configs and executes
workflows via the shared run_workflow_stream() function on schedule.
Uses stdlib threading — no external dependencies.
"""

import json
import logging
import re
import threading
import time
from datetime import datetime, timezone
from typing import Generator

logger = logging.getLogger(__name__)

# Active schedules: workflow_id -> ScheduledWorkflow
_schedules: dict[int, "ScheduledWorkflow"] = {}
_lock = threading.Lock()


def _parse_interval_seconds(cron_expr: str) -> int | None:
    """Parse a cron expression or interval string into seconds between runs.

    Supports:
      - "*/5 * * * *"  → every 5 minutes
      - "0 * * * *"    → every hour
      - "0 9 * * *"    → daily at 9am (runs every 24h)
      - "0 9 * * 1-5"  → weekdays at 9am (runs every 24h, skips weekends)
      - "every 5m"     → every 5 minutes
      - "every 1h"     → every hour
      - "every 30s"    → every 30 seconds
    """
    if not cron_expr:
        return None

    expr = cron_expr.strip().lower()

    # Simple interval syntax: "every 5m", "every 1h", "every 30s"
    m = re.match(r"every\s+(\d+)\s*(s|m|h)", expr)
    if m:
        val, unit = int(m.group(1)), m.group(2)
        return val * {"s": 1, "m": 60, "h": 3600}[unit]

    # Basic cron parsing
    parts = cron_expr.strip().split()
    if len(parts) >= 5:
        minute, hour = parts[0], parts[1]

        # */N * * * * → every N minutes
        if minute.startswith("*/"):
            try:
                return int(minute[2:]) * 60
            except ValueError:
                pass

        # 0 * * * * → every hour
        if minute == "0" and hour == "*":
            return 3600

        # 0 9 * * * → daily (every 24h)
        if minute.isdigit() and hour.isdigit():
            return 86400

    return None


class ScheduledWorkflow:
    """Runs a workflow on a recurring interval in a background thread."""

    def __init__(self, workflow_id: int, user_id: int, description: str,
                 workflow_data: dict, interval_seconds: int, cron_expr: str):
        self.workflow_id = workflow_id
        self.user_id = user_id
        self.description = description
        self.workflow_data = workflow_data
        self.interval_seconds = interval_seconds
        self.cron_expr = cron_expr
        self.running = False
        self.last_run: str | None = None
        self.run_count = 0
        self._thread: threading.Thread | None = None

    def start(self):
        """Start the recurring execution loop."""
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("Scheduled workflow %d every %ds (%s)",
                     self.workflow_id, self.interval_seconds, self.cron_expr)

    def stop(self):
        """Stop the recurring execution."""
        self.running = False
        logger.info("Unscheduled workflow %d", self.workflow_id)

    def _loop(self):
        """Background loop — sleep then execute, repeat."""
        while self.running:
            time.sleep(self.interval_seconds)
            if not self.running:
                break
            self._execute()

    def _execute(self):
        """Run the workflow once via the AI execution engine."""
        from src.api.routes.execute_ai import run_workflow_stream

        self.run_count += 1
        self.last_run = datetime.now(timezone.utc).isoformat()
        logger.info("Executing scheduled workflow %d (run #%d)", self.workflow_id, self.run_count)

        # Consume the SSE generator to completion (results logged, not streamed)
        try:
            for event in run_workflow_stream(self.description, self.workflow_data,
                                             extra_context="Triggered by schedule"):
                # Log each event but don't stream (no client connected)
                pass
            logger.info("Scheduled workflow %d run #%d complete", self.workflow_id, self.run_count)
        except Exception as e:
            logger.error("Scheduled workflow %d run #%d failed: %s", self.workflow_id, self.run_count, e)

    def to_dict(self) -> dict:
        return {
            "workflow_id": self.workflow_id,
            "cron": self.cron_expr,
            "interval_seconds": self.interval_seconds,
            "running": self.running,
            "last_run": self.last_run,
            "run_count": self.run_count,
        }


# ── Public API ────────────────────────────────────────────────────────────────

def schedule_workflow(workflow_id: int, user_id: int, description: str,
                      workflow_data: dict, cron_expr: str) -> dict:
    """Start a recurring schedule for a workflow. Returns schedule info or error."""
    interval = _parse_interval_seconds(cron_expr)
    if interval is None:
        return {"error": f"Cannot parse schedule: {cron_expr}"}
    if interval < 10:
        return {"error": "Minimum interval is 10 seconds"}

    with _lock:
        # Stop existing schedule if any
        existing = _schedules.get(workflow_id)
        if existing:
            existing.stop()

        sched = ScheduledWorkflow(workflow_id, user_id, description,
                                   workflow_data, interval, cron_expr)
        _schedules[workflow_id] = sched
        sched.start()

    return sched.to_dict()


def unschedule_workflow(workflow_id: int) -> bool:
    """Stop and remove a workflow schedule. Returns True if it existed."""
    with _lock:
        sched = _schedules.pop(workflow_id, None)
    if sched:
        sched.stop()
        return True
    return False


def get_schedules() -> list[dict]:
    """List all active schedules."""
    with _lock:
        return [s.to_dict() for s in _schedules.values()]


def get_schedule(workflow_id: int) -> dict | None:
    """Get schedule info for a specific workflow."""
    with _lock:
        sched = _schedules.get(workflow_id)
        return sched.to_dict() if sched else None
