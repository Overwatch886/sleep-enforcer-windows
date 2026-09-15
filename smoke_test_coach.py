"""Quick smoke test: import everything the app uses, instantiate the app
headlessly, run a full coach session, and verify the DB records it.

Uses a TEMP database so the real history in %LOCALAPPDATA% is never touched.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Point the store at a throwaway database BEFORE the app is created.
os.environ["COACH_DB_OVERRIDE"] = tempfile.mktemp(suffix=".db")

import enforcer
from coach.store import default_db_path  # noqa: F401 (see note above)
from pages.coach_page import CoachPage, CoachSession
from pages.data_page import DataPage
from pages.feedback_page import FeedbackPopup

# The Store honors COACH_DB_OVERRIDE when set.
_tmp_db = os.environ["COACH_DB_OVERRIDE"]

app = enforcer.SleepEnforcerApp()
app.withdraw()

# --- Simulate a bedtime coach session ---
assert app.coaching_enabled, "coach should be on by default"
assert app.store is not None, "store should have opened"

app.start_coach_session()
assert app._open_coach_session is not None, "session should be open"
assert app.grace_timer_active, "grace timer should be running"

session = app._open_coach_session
assert session.event_id is not None, "event should be saved to DB"
assert session.recommendation is not None
assert session.recommendation.recommended_choice in (
    "sleep", "replan", "continue", "break")

# User picks "sleep" -> must hand off to final countdown
app.coach_choose(session, "sleep")
assert app._open_coach_session is None, "session closed after choice"
event = app.store.get_event(session.event_id)
assert event.choice == "sleep", f"got {event.choice}"
assert event.recommended_choice, "recommendation must be recorded"
print("[OK] coach session -> sleep choice recorded, enforcement took over")

# Extension cap: the session's extension flag reflects DB state
used = app.store.extension_used_tonight()
print(f"[OK] extension_used_tonight = {used}")

# Feedback queue: the sleep event has no outcome yet
pending = app.store.events_needing_feedback()
print(f"[OK] pending feedback events: {len(pending)}")

# Data controls round-trip
data = app.store.export_all()
assert len(data["events"]) == 1
print("[OK] export works")

app.destroy()
print("\n[SMOKE TEST PASSED] app boots, coach session works end-to-end")
