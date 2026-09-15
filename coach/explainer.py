"""Turns a Recommendation into simple sentences (design.md, explainer).

Rules from plan.md FR-6/FR-7:
  - Personal history evidence is visually distinct from general estimates,
    so history-based sentences always start with "From your history:".
  - Estimates are labeled as estimates, never guarantees.
  - Respectful, non-shaming language. No threats, no medical claims.
"""
from coach.schemas import Recommendation, TaskDetails

_CHOICE_LABELS = {
    "sleep": "Sleep now",
    "replan": "Replan for later",
    "continue": "Continue for a bounded extension",
    "break": "Take a short break first",
}


def choice_label(choice: str) -> str:
    return _CHOICE_LABELS.get(choice, choice)


def build_explanation(recommendation: Recommendation,
                      task: TaskDetails,
                      extension_minutes: int = 30) -> str:
    """One short paragraph explaining the recommendation."""
    best = recommendation.recommended_choice
    parts = []

    if recommendation.limited_data:
        parts.append(
            "I don't have enough history to know your patterns yet, "
            "so this is based on what you just told me and your schedule. "
        )

    # The main reason(s) — at most the first two score reasons.
    for opt in recommendation.options:
        if opt.choice == best and opt.reasons:
            parts.append(" ".join(opt.reasons[:2]) + " ")

    # Honest notes for special cases.
    if best == "continue" and not recommendation.continue_available:
        parts.append("(The extension cap is already used tonight.) ")
    if best == "sleep":
        parts.append(
            f"You're set to wake at your usual time — sleeping now keeps "
            f"the full night. "
        )
    if best == "replan":
        parts.append(
            "I'll save the task with a time slot for tomorrow, and you "
            "keep the full night of sleep. "
        )

    return "".join(parts).strip()


def build_comparison(task: TaskDetails,
                     extension_minutes: int = 30,
                     extension_available: bool = True) -> dict:
    """The two-sided 'if you continue vs if you sleep' block (FR-6).

    Returns plain strings ready for the screen. Historical evidence is
    prefixed with 'From your history:' so it reads differently from the
    generic estimates.
    """
    fits = task.est_minutes <= extension_minutes

    continue_lines = []
    if not extension_available:
        continue_lines.append("Not available — tonight's extension is used up.")
    else:
        if fits:
            continue_lines.append(
                f"About {task.est_minutes} min of work done (estimate)."
            )
        else:
            continue_lines.append(
                f"You need ~{task.est_minutes} min but only "
                f"{extension_minutes} min fit — it likely won't finish (estimate)."
            )
        continue_lines.append(f"−{extension_minutes} min of sleep (estimate).")

    sleep_lines = [
        "Full night of sleep kept (estimate).",
        "Task can be slotted for tomorrow — pick a time in Replan.",
    ]

    return {"continue": continue_lines, "sleep": sleep_lines}
