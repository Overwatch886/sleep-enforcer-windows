"""Scores the four bedtime choices (design.md, section 5).

Plain arithmetic, no Tkinter. Every score change is recorded as a
human-readable reason string so the bedtime screen (and later dashboard)
can always show WHY a recommendation was made (plan.md FR-5..FR-7).

Weights are starting points — they will be tuned from real usage once
outcomes accumulate. The important part is that each term is small,
explainable, and stored.
"""
from typing import List, Optional

from coach.schemas import (
    Recommendation,
    ScoredOption,
    TaskDetails,
)
from coach.store import Store

CHOICES = ("sleep", "replan", "continue", "break")

# --- Starting weights (design.md section 5) ---
W_NOT_IMPORTANT_BONUS = 20      # sleep: task isn't important
W_NOT_URGENT_BONUS = 15         # sleep: task isn't urgent
W_REGRET_PATTERN_BONUS = 15     # sleep: similar nights ended in regret
W_GOAL_BONUS = 10               # sleep: a goal tag backs sleeping
W_URGENT_BONUS = 25             # continue: task is urgent
W_IMPORTANT_BONUS = 15          # continue: task is important
W_SLEEP_COST_PER_30MIN = 10     # continue: cost of lost sleep
W_REPLAN_IMPORTANT_BONUS = 20   # replan: important but not urgent
W_LOW_PERFORMANCE_BONUS = 10    # replan: this hour is historically weak
W_URGENT_REPLAN_PENALTY = 25    # replan: delaying an urgent task hurts
W_BREAK_BASE = 30
W_BREAK_STRICT_BONUS = 15
W_LONG_STRETCH_BONUS = 10       # break: at the PC a long time


class Recommender:
    def __init__(self, store: Store):
        self.store = store

    def recommend(self, task: TaskDetails,
                  extension_available: bool,
                  extension_minutes: int = 30,
                  strict_break_mode: bool = True,
                  long_stretch: bool = False) -> Recommendation:
        """Score all four options and pick the best one.

        `long_stretch` — True when the user has been at the PC for hours
        without a break (the caller decides the threshold).
        """
        history = self.store.recent_events(limit=50)

        options: List[ScoredOption] = [
            self._score_sleep(task, history),
            self._score_replan(task, history),
            self._score_continue(task, extension_available, extension_minutes),
            self._score_break(strict_break_mode, long_stretch),
        ]

        best = max(options, key=lambda o: o.score)
        return Recommendation(
            recommended_choice=best.choice,
            options=options,
            limited_data=len(history) == 0,
            continue_available=extension_available,
        )

    # --- individual scorers ---

    def _score_sleep(self, task: TaskDetails, history: list) -> ScoredOption:
        opt = ScoredOption(choice="sleep", score=50)
        if task.importance <= 2:
            opt.score += W_NOT_IMPORTANT_BONUS
            opt.reasons.append("This isn't important to you.")
        # The not-urgent bonus only pushes toward plain sleep when the task
        # also doesn't matter — an important task needs a replan slot, which
        # is scored under "replan" instead.
        if task.urgency <= 2 and task.importance <= 2:
            opt.score += W_NOT_URGENT_BONUS
            opt.reasons.append("This isn't urgent.")
        regret_nights = self._regretted_continue_nights(history, task.category)
        if regret_nights >= 2:
            opt.score += W_REGRET_PATTERN_BONUS
            opt.reasons.append(
                f"Past {regret_nights} nights like this you said you "
                f"regretted staying up."
            )
        goals = self.store.active_goals()
        if any(self._goal_matches_sleep(g) for g in goals):
            opt.score += W_GOAL_BONUS
            opt.reasons.append('Your goal says: "Protect my 8 hours of sleep".')
        return opt

    def _score_replan(self, task: TaskDetails, history: list) -> ScoredOption:
        opt = ScoredOption(choice="replan", score=50)
        if task.importance >= 4 and task.urgency <= 2:
            opt.score += W_REPLAN_IMPORTANT_BONUS
            opt.reasons.append(
                "Important but not urgent — a fresh slot tomorrow fits this better."
            )
        if self._late_hour_low_performance(history):
            opt.score += W_LOW_PERFORMANCE_BONUS
            opt.reasons.append(
                "Work you did this late hasn't gone well before."
            )
        if task.urgency >= 4:
            opt.score -= W_URGENT_REPLAN_PENALTY
            opt.reasons.append("But this is urgent — delaying it has a cost.")
        return opt

    def _score_continue(self, task: TaskDetails,
                        extension_available: bool,
                        extension_minutes: int) -> ScoredOption:
        opt = ScoredOption(choice="continue", score=50)
        if not extension_available:
            opt.score = 0
            opt.reasons.append("Tonight's extension is already used up.")
            return opt
        if task.urgency >= 4:
            opt.score += W_URGENT_BONUS
            opt.reasons.append("This genuinely is urgent.")
        if task.importance >= 4:
            opt.score += W_IMPORTANT_BONUS
            opt.reasons.append("This matters to you.")
        if task.est_minutes > extension_minutes:
            opt.score -= W_SLEEP_COST_PER_30MIN
            opt.reasons.append(
                f"You said it needs {task.est_minutes} min but the cap is "
                f"{extension_minutes} min — it won't fit."
            )
        else:
            opt.reasons.append(
                f"It fits inside the {extension_minutes}-minute extension."
            )
        opt.score -= W_SLEEP_COST_PER_30MIN
        opt.reasons.append(
            f"Costs about {extension_minutes} minutes of sleep."
        )
        return opt

    def _score_break(self, strict_break_mode: bool,
                     long_stretch: bool) -> ScoredOption:
        opt = ScoredOption(choice="break", score=W_BREAK_BASE)
        if strict_break_mode:
            opt.score += W_BREAK_STRICT_BONUS
            opt.reasons.append("Break mode is on in your settings.")
        if long_stretch:
            opt.score += W_LONG_STRETCH_BONUS
            opt.reasons.append("You've been at the PC a long stretch.")
        return opt

    # --- history helpers ---

    def _regretted_continue_nights(self, history: list,
                                   category: Optional[str]) -> int:
        """How many past 'continue' nights with this category ended in regret."""
        count = 0
        for event in history:
            if event.choice != "continue" or event.task is None:
                continue
            if category and event.task.category not in (category, "unknown"):
                continue
            outcome = self.store.outcome_for_event(event.id)
            if outcome in ("regretted", "overslept", "late"):
                count += 1
        return count

    def _late_hour_low_performance(self, history: list) -> bool:
        """True when late-night continues mostly ended badly (regret/oversleep/late)."""
        continues = [e for e in history if e.choice == "continue"]
        if len(continues) < 3:
            return False  # not enough evidence — never guess (US-6)
        bad = 0
        for event in continues:
            outcome = self.store.outcome_for_event(event.id)
            if outcome in ("regretted", "overslept", "late"):
                bad += 1
        return bad / len(continues) >= 0.5

    @staticmethod
    def _goal_matches_sleep(goal_text: str) -> bool:
        g = goal_text.lower()
        return "sleep" in g or "8 hours" in g or "health" in g
