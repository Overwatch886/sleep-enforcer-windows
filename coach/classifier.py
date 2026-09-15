"""Guesses what the user is doing at bedtime (design.md, section 4).

Priority order:
  1. The user's own rules (category_rules)        — highest trust
  2. The built-in program list (schemas)          — known apps only
  3. History: past corrections for this program   — learns from you
  4. Unknown — shown honestly as unknown, never guessed as fact (FR-3)

Every guess carries a confidence (0..1) and a human-readable evidence
string so the bedtime screen can always show WHY.
"""
from typing import Optional

from coach.schemas import (
    AMBIGUOUS_PROGRAMS,
    BUILTIN_PROGRAM_RULES,
    CATEGORIES,
    Classification,
)
from coach.store import Store

# Built-ins are trusted, but the user can override them, so they rank just
# below user rules in confidence.
_BUILTIN_CONFIDENCE = 0.8
# History needs several consistent corrections before it's trusted.
_HISTORY_MIN_SAMPLES = 3
_HISTORY_CONFIDENCE_BASE = 0.5


class Classifier:
    def __init__(self, store: Store):
        self.store = store

    def classify(self, program_name: str) -> Classification:
        """Classify the current activity from the foreground program name."""
        program = (program_name or "").lower().strip()
        if not program:
            return Classification(
                category="unknown", confidence=0.0,
                evidence="No program information available.",
                source="unknown",
            )

        # 1. User's own rules — highest priority.
        for rule in self.store.user_category_rules():
            if rule["program_name"] == program:
                return Classification(
                    category=rule["category"],
                    confidence=0.95,
                    evidence=f"Your own rule: {program} counts as {rule['category']}.",
                    source="user_rule",
                )

        # 2. Built-in list — but ambiguous programs (browsers etc.) are
        #    never classified by name alone; only a user rule or history can.
        if program not in AMBIGUOUS_PROGRAMS:
            for name, category in BUILTIN_PROGRAM_RULES:
                if name == program:
                    return Classification(
                        category=category,
                        confidence=_BUILTIN_CONFIDENCE,
                        evidence=f"Known application ({name} is usually {category}).",
                        source="builtin",
                    )

        # 3. History — how you corrected this program before.
        counts = self.store.correction_counts_for_program(program)
        total = sum(counts.values())
        if total >= _HISTORY_MIN_SAMPLES:
            best_category, best_n = max(counts.items(), key=lambda kv: kv[1])
            if best_category in CATEGORIES and best_n / total >= 0.5:
                confidence = min(
                    0.9,
                    _HISTORY_CONFIDENCE_BASE + 0.1 * best_n,
                )
                return Classification(
                    category=best_category,
                    confidence=confidence,
                    evidence=(
                        f"From your history: you've corrected {program} "
                        f"to {best_category} {best_n} of {total} times."
                    ),
                    source="history",
                )

        # 4. Unknown — honest by design.
        if program in AMBIGUOUS_PROGRAMS:
            evidence = (
                f"{program} can be work or play — the program name alone "
                f"can't tell. Tell me what you're doing."
            )
        else:
            evidence = f"I don't recognize {program} yet."
        return Classification(
            category="unknown", confidence=0.0,
            evidence=evidence, source="unknown",
        )

    def learn_correction(self, event_id: Optional[int], program_name: str,
                         guessed_category: str, corrected_category: str,
                         make_rule: bool = False):
        """Record a user correction; optionally also save it as a rule.

        Corrections NEVER rewrite past events (US-2) — they only shape
        future guesses.
        """
        if not program_name:
            return
        self.store.save_classification_correction(
            event_id, program_name, guessed_category, corrected_category
        )
        if make_rule:
            self.store.upsert_category_rule(program_name, corrected_category)
