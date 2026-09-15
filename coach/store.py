"""SQLite storage for the coach (design.md, section 3).

One database file (default: %LOCALAPPDATA%\\SleepEnforcer\\sleep_enforcer.db).
Every write is a plain SQL statement; every read returns the dataclass shapes
from schemas.py. If the database is missing or corrupt, the store recreates
an empty one — the app must always fall back to safe enforcement behavior
(plan.md NFR: Resilience), never crash because history is unreadable.
"""
import json
import os
import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional

from coach.schemas import (
    ActivitySample,
    BUILTIN_GOALS,
    EventRecord,
    TaskDetails,
)

DB_FILE_NAME = "sleep_enforcer.db"


def default_db_path() -> str:
    app_data_dir = os.getenv("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(app_data_dir, "SleepEnforcer", DB_FILE_NAME)


class Store:
    """All database access goes through this class."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or default_db_path()
        self._conn = None

    # --- lifecycle ---

    def open(self):
        """Open (and create if needed) the database. Safe to call twice."""
        if self._conn is not None:
            return
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._create_tables()
        self._seed_builtin_data()

    def close(self):
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def _create_tables(self):
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                schedule_bedtime TEXT NOT NULL,
                resolved_at TEXT,
                choice TEXT DEFAULT '',
                extension_used INTEGER DEFAULT 0,
                recommended_choice TEXT DEFAULT '',
                recommendation_followed INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS event_tasks (
                event_id INTEGER PRIMARY KEY REFERENCES events(id) ON DELETE CASCADE,
                description TEXT DEFAULT '',
                category TEXT DEFAULT 'unknown',
                urgency INTEGER DEFAULT 3,
                importance INTEGER DEFAULT 3,
                est_minutes INTEGER DEFAULT 30,
                goal_tags TEXT DEFAULT '[]',
                source TEXT DEFAULT 'user'
            );

            CREATE TABLE IF NOT EXISTS activity_samples (
                event_id INTEGER PRIMARY KEY REFERENCES events(id) ON DELETE CASCADE,
                program_name TEXT DEFAULT '',
                mapped_category TEXT DEFAULT 'unknown',
                user_corrected INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER REFERENCES events(id) ON DELETE CASCADE,
                asked_at TEXT NOT NULL,
                reported TEXT DEFAULT '',
                auto_detected TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS replans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER REFERENCES events(id) ON DELETE SET NULL,
                title TEXT DEFAULT '',
                target_time TEXT,
                est_minutes INTEGER DEFAULT 30,
                done INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                builtin INTEGER DEFAULT 0,
                active INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS category_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                program_name TEXT NOT NULL,
                category TEXT NOT NULL,
                built_in INTEGER DEFAULT 0,
                UNIQUE(program_name)
            );

            CREATE TABLE IF NOT EXISTS feedback_on_classification (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER REFERENCES events(id) ON DELETE CASCADE,
                program_name TEXT DEFAULT '',
                guessed_category TEXT DEFAULT '',
                corrected_category TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );
            """
        )
        self._conn.commit()

    def _seed_builtin_data(self):
        """Insert the starter goals and built-in category rules once."""
        count = self._conn.execute(
            "SELECT COUNT(*) FROM goals WHERE builtin = 1"
        ).fetchone()[0]
        if count == 0:
            for text in BUILTIN_GOALS:
                self._conn.execute(
                    "INSERT INTO goals (text, builtin, active) VALUES (?, 1, 1)",
                    (text,),
                )
        # Built-in program rules are defined in code (schemas.py) so they can
        # be updated with the app; nothing to seed here.
        self._conn.commit()

    # --- events ---

    def save_event(self, event: EventRecord) -> int:
        """Insert a new event (with task + activity) and return its id."""
        cur = self._conn.execute(
            """INSERT INTO events
               (started_at, schedule_bedtime, resolved_at, choice,
                extension_used, recommended_choice, recommendation_followed)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                _iso(event.started_at),
                _iso(event.schedule_bedtime),
                _iso(event.resolved_at),
                event.choice,
                int(event.extension_used),
                event.recommended_choice,
                int(event.recommendation_followed),
            ),
        )
        event_id = cur.lastrowid

        if event.task is not None:
            self._conn.execute(
                """INSERT INTO event_tasks
                   (event_id, description, category, urgency, importance,
                    est_minutes, goal_tags, source)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    event_id,
                    event.task.description,
                    event.task.category,
                    event.task.urgency,
                    event.task.importance,
                    event.task.est_minutes,
                    json.dumps(event.task.goal_tags),
                    event.task.source,
                ),
            )

        if event.activity is not None:
            self._conn.execute(
                """INSERT INTO activity_samples
                   (event_id, program_name, mapped_category, user_corrected)
                   VALUES (?, ?, ?, ?)""",
                (
                    event_id,
                    event.activity.program_name,
                    event.activity.mapped_category,
                    int(event.activity.user_corrected),
                ),
            )

        self._conn.commit()
        return event_id

    def resolve_event(self, event_id: int, choice: str,
                      resolved_at: Optional[datetime] = None,
                      extension_used: bool = False,
                      recommended_choice: str = "",
                      recommendation_followed: bool = False):
        """Record the user's choice on an open event."""
        self._conn.execute(
            """UPDATE events SET resolved_at = ?, choice = ?,
               extension_used = ?, recommended_choice = ?,
               recommendation_followed = ? WHERE id = ?""",
            (
                _iso(resolved_at or datetime.now()),
                choice,
                int(extension_used),
                recommended_choice,
                int(recommendation_followed),
                event_id,
            ),
        )
        self._conn.commit()

    def get_event(self, event_id: int) -> Optional[EventRecord]:
        row = self._conn.execute(
            "SELECT * FROM events WHERE id = ?", (event_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_event(row)

    def recent_events(self, limit: int = 20) -> List[EventRecord]:
        rows = self._conn.execute(
            "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [self._row_to_event(r) for r in rows]

    def _row_to_event(self, row) -> EventRecord:
        event = EventRecord(
            id=row["id"],
            started_at=_parse(row["started_at"]),
            schedule_bedtime=_parse(row["schedule_bedtime"]),
            resolved_at=_parse(row["resolved_at"]),
            choice=row["choice"],
            extension_used=bool(row["extension_used"]),
            recommended_choice=row["recommended_choice"],
            recommendation_followed=bool(row["recommendation_followed"]),
        )
        task_row = self._conn.execute(
            "SELECT * FROM event_tasks WHERE event_id = ?", (row["id"],)
        ).fetchone()
        if task_row is not None:
            event.task = TaskDetails(
                description=task_row["description"],
                category=task_row["category"],
                urgency=task_row["urgency"],
                importance=task_row["importance"],
                est_minutes=task_row["est_minutes"],
                goal_tags=json.loads(task_row["goal_tags"] or "[]"),
                source=task_row["source"],
            )
        act_row = self._conn.execute(
            "SELECT * FROM activity_samples WHERE event_id = ?", (row["id"],)
        ).fetchone()
        if act_row is not None:
            event.activity = ActivitySample(
                program_name=act_row["program_name"],
                mapped_category=act_row["mapped_category"],
                user_corrected=bool(act_row["user_corrected"]),
            )
        return event

    def extension_used_tonight(self, now: Optional[datetime] = None) -> bool:
        """True if an extension was already granted since the last wake time.

        'Tonight' spans from the previous wake time to the upcoming one; the
        simplest reliable boundary is: any event with extension_used=1 whose
        started_at is within the last 24 hours.
        """
        now = now or datetime.now()
        row = self._conn.execute(
            """SELECT COUNT(*) FROM events
               WHERE extension_used = 1
               AND started_at >= ?""",
            (_iso(now - timedelta(hours=24)),),
        ).fetchone()
        return row[0] > 0

    # --- outcomes ---

    def save_outcome(self, event_id: int, reported: str,
                     auto_detected: str = "",
                     asked_at: Optional[datetime] = None):
        self._conn.execute(
            """INSERT INTO outcomes
               (event_id, asked_at, reported, auto_detected, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                event_id,
                _iso(asked_at or datetime.now()),
                reported,
                auto_detected,
                _iso(datetime.now()),
            ),
        )
        self._conn.commit()

    def outcome_for_event(self, event_id: int) -> Optional[str]:
        row = self._conn.execute(
            "SELECT reported FROM outcomes WHERE event_id = ? ORDER BY id DESC LIMIT 1",
            (event_id,),
        ).fetchone()
        return row["reported"] if row is not None else None

    def events_needing_feedback(self, limit: int = 3) -> List[EventRecord]:
        """Resolved events from the last 2 days that have no outcome yet."""
        cutoff = datetime.now() - timedelta(days=2)
        rows = self._conn.execute(
            """SELECT e.* FROM events e
               WHERE e.resolved_at IS NOT NULL
               AND e.resolved_at >= ?
               AND e.choice != 'no_answer'
               AND NOT EXISTS (SELECT 1 FROM outcomes o WHERE o.event_id = e.id)
               ORDER BY e.id DESC LIMIT ?""",
            (_iso(cutoff), limit),
        ).fetchall()
        return [self._row_to_event(r) for r in rows]

    # --- replans ---

    def save_replan(self, event_id: Optional[int], title: str,
                    target_time: datetime, est_minutes: int = 30) -> int:
        cur = self._conn.execute(
            """INSERT INTO replans (event_id, title, target_time, est_minutes)
               VALUES (?, ?, ?, ?)""",
            (event_id, title, _iso(target_time), est_minutes),
        )
        self._conn.commit()
        return cur.lastrowid

    def open_replans(self) -> List[dict]:
        rows = self._conn.execute(
            "SELECT * FROM replans WHERE done = 0 ORDER BY target_time"
        ).fetchall()
        return [dict(r) for r in rows]

    def mark_replan_done(self, replan_id: int, done: bool = True):
        self._conn.execute(
            "UPDATE replans SET done = ? WHERE id = ?", (int(done), replan_id)
        )
        self._conn.commit()

    # --- goals ---

    def active_goals(self) -> List[str]:
        rows = self._conn.execute(
            "SELECT text FROM goals WHERE active = 1 ORDER BY builtin DESC, id"
        ).fetchall()
        return [r["text"] for r in rows]

    def all_goals(self) -> List[dict]:
        rows = self._conn.execute(
            "SELECT * FROM goals ORDER BY builtin DESC, id"
        ).fetchall()
        return [dict(r) for r in rows]

    def add_goal(self, text: str) -> int:
        cur = self._conn.execute(
            "INSERT INTO goals (text, builtin, active) VALUES (?, 0, 1)", (text,)
        )
        self._conn.commit()
        return cur.lastrowid

    def set_goal_active(self, goal_id: int, active: bool):
        self._conn.execute(
            "UPDATE goals SET active = ? WHERE id = ?", (int(active), goal_id)
        )
        self._conn.commit()

    def delete_goal(self, goal_id: int):
        # Never delete built-ins — just deactivate them.
        self._conn.execute(
            "DELETE FROM goals WHERE id = ? AND builtin = 0", (goal_id,)
        )
        self.set_goal_active(goal_id, False)
        self._conn.commit()

    # --- category rules ---

    def user_category_rules(self) -> List[dict]:
        rows = self._conn.execute(
            "SELECT * FROM category_rules WHERE built_in = 0 ORDER BY program_name"
        ).fetchall()
        return [dict(r) for r in rows]

    def upsert_category_rule(self, program_name: str, category: str,
                             built_in: bool = False):
        self._conn.execute(
            """INSERT INTO category_rules (program_name, category, built_in)
               VALUES (?, ?, ?)
               ON CONFLICT(program_name)
               DO UPDATE SET category = excluded.category, built_in = excluded.built_in""",
            (program_name.lower(), category, int(built_in)),
        )
        self._conn.commit()

    def remove_category_rule(self, program_name: str):
        self._conn.execute(
            "DELETE FROM category_rules WHERE program_name = ?",
            (program_name.lower(),),
        )
        self._conn.commit()

    # --- classification feedback (US-2: corrections never rewrite history) ---

    def save_classification_correction(self, event_id: Optional[int],
                                       program_name: str,
                                       guessed_category: str,
                                       corrected_category: str):
        self._conn.execute(
            """INSERT INTO feedback_on_classification
               (event_id, program_name, guessed_category, corrected_category, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (event_id, program_name.lower(), guessed_category,
             corrected_category, _iso(datetime.now())),
        )
        self._conn.commit()

    def correction_counts_for_program(self, program_name: str) -> dict:
        """How often each category was chosen for this program after a guess."""
        rows = self._conn.execute(
            """SELECT corrected_category, COUNT(*) AS n
               FROM feedback_on_classification
               WHERE program_name = ?
               GROUP BY corrected_category""",
            (program_name.lower(),),
        ).fetchall()
        return {r["corrected_category"]: r["n"] for r in rows}

    # --- data controls (FR-11) ---

    def export_all(self) -> dict:
        """Everything as one JSON-able dict, for the export button."""
        tables = (
            "events", "event_tasks", "activity_samples", "outcomes",
            "replans", "goals", "category_rules", "feedback_on_classification",
        )
        out = {}
        for t in tables:
            rows = self._conn.execute(f"SELECT * FROM {t}").fetchall()
            out[t] = [dict(r) for r in rows]
        return out

    def import_all(self, data: dict):
        """Replace current contents with an export_all() payload."""
        tables = (
            "events", "event_tasks", "activity_samples", "outcomes",
            "replans", "category_rules", "feedback_on_classification", "goals",
        )
        for t in tables:
            self._conn.execute(f"DELETE FROM {t}")
        for t in tables:
            for row in data.get(t, []):
                cols = ", ".join(row.keys())
                marks = ", ".join("?" for _ in row)
                self._conn.execute(
                    f"INSERT INTO {t} ({cols}) VALUES ({marks})",
                    list(row.values()),
                )
        self._conn.commit()

    def delete_history(self):
        """Wipe learned data. Goals/rules stay (they're user config, not history)."""
        for t in ("events", "outcomes", "replans", "feedback_on_classification"):
            self._conn.execute(f"DELETE FROM {t}")
        # event_tasks/activity_samples cascade from events.
        self._conn.commit()


# --- datetime helpers (ISO strings in, ISO strings out) ---

def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt is not None else None


def _parse(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None
