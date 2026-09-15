"""Shared data shapes for the coach brain (design.md, section 3).

Plain classes only — no Tkinter, no I/O. These are the values that flow
between the store, the classifier, the recommender, and the screens.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


# --- Categories (design.md section 3, event_tasks.category) ---

CATEGORIES = (
    "work",
    "study",
    "obligation",
    "recovery",
    "leisure",
    "distraction",
    "unknown",
)

# The starter goals offered in settings (design.md section 8).
# The user can edit/deactivate these and add their own.
BUILTIN_GOALS = (
    "Protect my 8 hours of sleep",
    "Finish my degree with good grades",
    "Be sharp and on time in the morning",
    "Health comes before entertainment",
)

# Broad built-in program-name -> category mappings used when the user has
# no custom rule and no history yet (design.md section 4, step 3).
# Names are matched case-insensitively, exact process name first, then
# substring. Anything unmatched stays "unknown" — never guessed as fact.
BUILTIN_PROGRAM_RULES = (
    # work
    ("code.exe", "work"), ("pycharm64.exe", "work"), ("idea64.exe", "work"),
    ("devenv.exe", "work"), ("winword.exe", "work"), ("excel.exe", "work"),
    ("powerpnt.exe", "work"), ("outlook.exe", "work"), ("teams.exe", "work"),
    ("slack.exe", "work"), ("zoom.exe", "work"),
    # study
    ("anki.exe", "study"), ("onenote.exe", "study"), ("notion.exe", "study"),
    # distraction
    ("steam.exe", "distraction"), ("steamwebhelper.exe", "distraction"),
    ("epicgameslauncher.exe", "distraction"), ("discord.exe", "distraction"),
    ("riotclientservices.exe", "distraction"),
    # leisure
    ("vlc.exe", "leisure"), ("spotify.exe", "leisure"),
    ("netflix.exe", "leisure"), ("youtube.exe", "leisure"),
)
# Programs where the program name alone can't tell work from play.
# These stay "unknown" from the built-in list; only user rules or history
# can classify them.
AMBIGUOUS_PROGRAMS = ("chrome.exe", "msedge.exe", "firefox.exe", "explorer.exe")


@dataclass
class TaskDetails:
    """What the user said they were doing (design.md, event_tasks)."""
    description: str = ""
    category: str = "unknown"          # one of CATEGORIES
    urgency: int = 3                   # 1 (not urgent) .. 5 (right now)
    importance: int = 3                # 1 (not important) .. 5 (critical)
    est_minutes: int = 30              # how long the user says it needs
    goal_tags: List[str] = field(default_factory=list)
    source: str = "user"               # "user" or "auto" (app guess)


@dataclass
class ActivitySample:
    """Privacy-minimized program snapshot (design.md, activity_samples)."""
    program_name: str = ""             # e.g. "chrome.exe" — name only
    mapped_category: str = "unknown"
    user_corrected: bool = False


@dataclass
class EventRecord:
    """One bedtime interruption (design.md, events)."""
    started_at: datetime = None
    schedule_bedtime: datetime = None
    resolved_at: Optional[datetime] = None
    choice: str = ""                   # sleep/continue/replan/break/no_answer
    extension_used: bool = False
    recommended_choice: str = ""
    recommendation_followed: bool = False
    task: Optional[TaskDetails] = None
    activity: Optional[ActivitySample] = None
    id: Optional[int] = None


@dataclass
class Classification:
    """The classifier's guess about the current activity (design.md, section 4)."""
    category: str = "unknown"
    confidence: float = 0.0            # 0.0 .. 1.0
    evidence: str = ""                 # why — shown on screen
    source: str = "unknown"            # user_rule / builtin / history / unknown

    @property
    def confidence_label(self) -> str:
        if self.confidence >= 0.75:
            return "high"
        if self.confidence >= 0.4:
            return "medium"
        if self.confidence > 0.0:
            return "low"
        return "none"


@dataclass
class ScoredOption:
    """One scored choice for a bedtime event (design.md, section 5)."""
    choice: str                        # sleep/continue/replan/break
    score: int = 0                     # 0 .. 100
    reasons: List[str] = field(default_factory=list)


@dataclass
class Recommendation:
    """The recommender's full output for one bedtime event."""
    recommended_choice: str = ""
    options: List[ScoredOption] = field(default_factory=list)
    explanation: str = ""              # built by explainer.py
    limited_data: bool = False         # True when no personal history yet
    continue_available: bool = True    # False when tonight's extension is spent
