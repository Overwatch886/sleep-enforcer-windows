"""Learns habits from history (design.md, section 2, patterns.py).

Feeds the recommender and the screens with simple, honest pattern facts.
Every function returns evidence-style strings and counts — never a claim
without enough samples behind it (plan.md US-6: no fabricated patterns).
"""
from datetime import datetime, timedelta
from typing import List, Optional

from coach.store import Store

# A pattern is only reported when at least this many events back it up.
MIN_SAMPLES = 3


class Patterns:
    def __init__(self, store: Store):
        self.store = store

    def common_late_categories(self, limit: int = 20) -> List[tuple]:
        """What the user is usually doing at bedtime: [(category, count), ...].

        Only categories that showed up at least MIN_SAMPLES times.
        """
        counts = {}
        for event in self.store.recent_events(limit=limit):
            if event.task is not None and event.task.category != "unknown":
                cat = event.task.category
                counts[cat] = counts.get(cat, 0) + 1
        return sorted(
            [(c, n) for c, n in counts.items() if n >= MIN_SAMPLES],
            key=lambda kv: kv[1], reverse=True,
        )

    def extension_rate(self, limit: int = 20) -> Optional[float]:
        """Share of bedtime events that ended in 'continue'. None if not enough data."""
        events = self.store.recent_events(limit=limit)
        resolved = [e for e in events if e.choice in ("continue", "sleep", "replan", "break")]
        if len(resolved) < MIN_SAMPLES:
            return None
        continues = sum(1 for e in resolved if e.choice == "continue")
        return continues / len(resolved)

    def outcome_rate(self, outcome: str, limit: int = 50) -> Optional[float]:
        """Share of reported outcomes equal to `outcome`. None if not enough data."""
        events = self.store.recent_events(limit=limit)
        reported = []
        for e in events:
            outcome_value = self.store.outcome_for_event(e.id)
            if outcome_value:
                reported.append(outcome_value)
        if len(reported) < MIN_SAMPLES:
            return None
        return sum(1 for r in reported if r == outcome) / len(reported)

    def pc_resume_time_yesterday(self) -> Optional[datetime]:
        """Best-effort auto-detect of when the PC came back on (design.md,
        feedback popup). Looks for a long gap between logged events; this is
        a fallback signal only — the user's own report always wins."""
        events = self.store.recent_events(limit=20)
        # The last event before the gap is the last activity of the night;
        # the first event after is the first activity of the next day.
        for i in range(len(events) - 1):
            older, newer = events[i], events[i + 1]
            if older.started_at is None or newer.started_at is None:
                continue
            gap = older.started_at - newer.started_at  # events come newest-first
            if gap > timedelta(hours=6):
                return newer.started_at
        return None
