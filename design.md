# Sleep Enforcer Habit Coach — Technical Design

This document explains **how** we will build what `plan.md` describes.
Written in plain language. Read alongside `plan.md`.

---

## 1. The big picture

Today the app works like this:

```
Bedtime → "Why are you up?" → keyword match? → 30 min extension → repeat forever
```

It will work like this:

```
Bedtime → Coach screen:
            1. Shows what it thinks you're doing (from the program in front)
            2. Asks you to confirm/fix: what, how urgent, how important, how long
            3. Shows a recommendation with reasons and a "if you continue vs if you sleep" comparison
            4. You pick: Sleep / Replan / Continue (bounded) / Take a break
            5. Your choice goes to the existing enforcement machinery
            6. Everything is saved to learn from next time
```

**The enforcement code you already have does not get replaced.** It becomes the
safety net that catches the cases where you don't answer or the coach fails.

### Golden rule of the design

All "thinking" code (scoring, pattern learning, guessing categories) lives in
**plain Python files with no Tkinter**. The screens only display results and
collect clicks. This is required by `plan.md` (testability) and lets us test
the brain without opening any windows.

---

## 2. New file layout

```
windows_app/
├── main.py                     # entry point (unchanged job: logging, lock, start app)
├── enforcer.py                 # SleepEnforcerApp (Tk controller) — extended, not rewritten
├── sleep_enforcer.py           # existing page frames + SingleInstance + DualLogger
│
├── coach/                      # NEW — the brain (no Tkinter allowed in here)
│   ├── __init__.py
│   ├── store.py                # SQLite database: save/load everything
│   ├── classifier.py           # guess what you're doing (program name + history + your rules)
│   ├── recommender.py          # score the 4 options, pick a recommendation
│   ├── explainer.py            # turn a recommendation into simple sentences
│   ├── patterns.py             # learn habits from history (late-night patterns, oversleep, regret)
│   ├── activity.py             # read the foreground program name (psutil/ctypes, name only)
│   └── schemas.py              # shared data shapes (Category, TaskDetails, Recommendation, ...)
│
├── pages/                      # NEW — new screens (Tkinter only, no logic)
│   ├── __init__.py
│   ├── coach_page.py           # the bedtime coach screen
│   ├── feedback_page.py        # the next-day "what happened?" popup
│   └── data_page.py            # settings screen section: data controls, goals, category rules
│
├── test_sleep_enforcer.py      # existing 4 schedule tests — MUST keep passing
├── test_coach.py               # NEW — headless tests for the brain
├── environment.yml             # + nothing new needed (sqlite3 is built into Python)
```

Why no new packages: SQLite is built into Python (`sqlite3`), process names come
from `psutil` (already used), foreground window title comes from `ctypes`
(already used for focus checks). Nothing to install.

---

## 3. The database (SQLite)

One file: `%LOCALAPPDATA%\SleepEnforcer\sleep_enforcer.db`
(existing `settings.json` stays for schedule settings; everything the coach
learns goes in the database).

Tables in plain words:

### `events` — one row every time bedtime (or warning) is reached
| Column | What it is |
|---|---|
| id | row number |
| started_at | when the bedtime prompt appeared |
| schedule_bedtime | the bedtime that triggered it |
| resolved_at | when you made your choice |
| choice | `sleep` / `continue` / `replan` / `break` / `no_answer` |
| extension_used | 1 if this event used the night's extension |
| recommended_choice | what the app suggested |
| recommendation_followed | 1 if you did what it suggested |

### `event_tasks` — what you said you were doing (one per event, optional)
| Column | What it is |
|---|---|
| event_id | links to the event |
| description | your optional free text |
| category | work / study / obligation / recovery / leisure / distraction / unknown |
| urgency | 1–5 |
| importance | 1–5 |
| est_minutes | how long you said it needs |
| goal_tags | which of your goals it relates to |
| source | `user` (you picked it) or `auto` (app guessed) |

### `activity_samples` — the privacy-minimized program snapshot
| Column | What it is |
|---|---|
| event_id | links to the event |
| program_name | e.g. `chrome.exe` (name only — never titles, never content) |
| mapped_category | what our rules mapped it to |
| user_corrected | 1 if you overrode the mapping |

### `outcomes` — what actually happened next day
| Column | What it is |
|---|---|
| event_id | links to the event |
| asked_at | when we asked you |
| reported | finished / postponed / overslept / late / regretted / rec_wrong / skipped |
| auto_detected | what the app noticed by itself (e.g. PC off until 10:14) |
| created_at | when recorded |

### `replans` — tasks you pushed to later
| Column | What it is |
|---|---|
| event_id | the bedtime event that created it |
| title | short task name |
| target_time | when you plan to do it |
| est_minutes | expected duration |
| done | 0/1 — marked done from the feedback popup |

### `goals` — your principles
| Column | What it is |
|---|---|
| text | the principle, e.g. "Protect my 8 hours" |
| builtin | 1 if it came from our starter list |
| active | 0/1 |

### `category_rules` — your custom program→category rules
| Column | What it is |
|---|---|
| program_name | e.g. `steam.exe` |
| category | what you say it counts as |
| built_in | 1 if it's one of ours |

### `feedback_on_classification` — when you say "you guessed wrong"
Kept so future guesses can avoid repeating the mistake. (User corrections never
rewrite past rows — a new row is added, per plan.md US-2.)

---

## 4. How the app guesses what you're doing (classifier)

At bedtime the app:

1. Asks Windows: **which program is in front right now?** (process name only)
2. Checks **your custom rules** first (`category_rules`) — highest priority.
3. Then its **built-in list** (browsers → leisure by default, known IDEs/Office
   tools → work, game launchers → distraction, media players → leisure, ...).
4. Then **history**: "last 6 times `chrome.exe` was in front at bedtime, you
   corrected it to *study* 5 times" → guess study, with confidence.
5. If nothing matches → **unknown**, shown honestly as unknown (never guessed
   as fact — plan.md FR-3).

Every guess carries a **confidence** (how sure) and **evidence** (why: which
rule or which past events). The screen always lets you fix it in one click,
and the fix is saved so the next guess is better.

**Privacy:** only the program name (like `chrome.exe`) is read and stored.
No window titles, no keystrokes, no screenshots, no file names, no browsing
history. Watching can be switched off in settings without touching the sleep
schedule (FR-11).

---

## 5. How the recommendation is made (recommender)

For every bedtime event the engine scores 4 options — **sleep**, **replan**,
**continue (bounded)**, **short break first** — each from 0 to 100.

Simple scoring sketch (exact weights tuned later from your real data):

```
sleep_score      = base 50
                 + importance bonus if task is NOT important
                 + urgency penalty  if task is NOT urgent
                 + pattern bonus    if you historically regretted
                                    continuing on similar nights
                 + goal bonus       if a goal tag says "protect sleep"

continue_score   = base 50
                 + urgency bonus    if task is urgent AND fits in the cap
                 + importance bonus if task is important
                 - sleep cost       (minutes of sleep lost, shown honestly)
                 - 100 if tonight's extension is already used
                 - pattern penalty  if similar nights ended in regret/oversleep

replan_score     = base 50
                 + bonus if task is important but not urgent
                 + bonus if this hour is historically low-performance for you
                 - penalty if task is genuinely urgent (delaying hurts)

break_score      = base 30
                 + bonus if the strict-break setting is on
                 + bonus if you've been at the PC a long stretch
```

The highest score wins and becomes the recommendation. Scores and the reasons
behind each term are stored so the screen (and later the dashboard) can show
**why**.

**New user, no history:** the pattern terms are simply 0, and the screen says
"Based on limited data — no personal history yet." Nothing is invented (US-6).

**Extension cap (locked decision):** one extension per night, 30 minutes,
configurable in settings. After it's used, `continue` is not offered — the
screen says why.

---

## 6. The bedtime coach screen (plain layout sketch)

```
┌────────────────────────────────────────────────────────┐
│  🌙 It's 22:00 — bedtime                               │
│                                                        │
│  Looks like you're in: chrome.exe  →  Study?  ✏️ Fix   │
│  (Guess confidence: medium — from your last 5 nights)  │
│                                                        │
│  What's going on?        [ Study ▾ ]  (required)       │
│  Urgency      ●●●○○   Importance  ●●●●○                │
│  Needs about: [30 min ▾]    (optional note: [______])  │
│                                                        │
│  ── My recommendation: SLEEP NOW ──                    │
│  "You marked this as important but not urgent, and     │
│   last 3 times you stayed up past 22:00 you reported   │
   regretting it. Your goal 'Protect my 8 hours' ..."    │
│                                                        │
│  If you continue:  +30 min work, −30 min sleep,        │
│                    history: 2 of 3 nights ended late   │
│  If you sleep:     task replanned to tomorrow 16:00,   │
│                    full 8h sleep (estimate)            │
│                                                        │
│  [ 😴 Sleep now ] [ 📅 Replan ] [ ▶ Continue 30m ]     │
│  [ ☕ Break first ]            [ Skip questions → ]     │
│                                                        │
│  ⏳ Grace timer: 2:41 (existing behavior if ignored)   │
└────────────────────────────────────────────────────────┘
```

Rules for this screen:

- **Non-blocking** like everything else — it's a Tk frame in the existing
  page system (`self.frames`), not a modal (`.agentrules` rule 4).
- The existing grace timer keeps running; if it expires with no answer →
  existing countdown → hibernate. Not answering never bypasses enforcement.
- "Skip questions" jumps straight to the choice buttons with category
  `unknown`.
- "Fix" on the guess opens your custom-rules editor inline (one row:
  program → category).

### Next-day feedback popup (non-blocking, skippable)

Appears after wake time (or when you first use the PC after waking):

```
Last night you chose: Continue (study, 30 min)
PC came back on at 06:12 (auto-detected)
What happened?  [Finished] [Postponed] [Overslept] [Late]
                [Regretted it] [Advice was wrong] [Skip]
Replanned task "Assignment draft" — done?  [Yes] [No]
```

Auto-detection fills in what it can, but **your one click is what gets
recorded** (your locked decision). One question per night, never nagging.

---

## 7. How choices hand off to the existing enforcement (FR-8)

| Your choice | What happens |
|---|---|
| **Sleep now** | Straight to the existing final countdown → hibernate |
| **Replan** | Task saved to `replans`, then same as sleep now |
| **Continue** | The existing extension path runs — but only if tonight's extension is unused; grace timer stops, extension flag set, resume normal watch |
| **Break first** | The existing `take_5mins_break()` runs, then you're asked again |
| **No answer** | Grace timeout → existing final countdown → hibernate |

Nothing new replaces the state machine (`grace_timer_active`,
`final_timer_active`, `extension_active`, `is_on_break`) — the coach just sets
those same flags.

---

## 8. Settings additions (existing SettingsPage, new sections)

- **Coaching:** on/off, intensity (gentle / normal / firm), extension minutes
- **Data:** view what's collected, turn program-watching off, export all data
  to a file, import, delete everything
- **Goals:** starter list + add your own, edit, deactivate
- **Category rules:** your program → category list, add/remove

Everything stays in `settings.json` (or moves to SQLite) — either way the
existing save/load pattern is kept.

---

## 9. Testing plan

1. **Existing 4 schedule tests keep passing untouched** — run before every
   commit (`test_sleep_enforcer.py`).
2. **New `test_coach.py`** — headless, no GUI:
   - classifier: rule priority, history-based guess, unknown case, corrections
   - recommender: urgent task → continue wins; important-not-urgent late at
     night → replan wins; extension already used → continue blocked; empty
     history → limited-data flag, no crash
   - store: save/load round-trips, corrupt DB → safe fallback (plan.md NFR
     resilience)
   - explainer: outputs always label estimates vs. personal history
3. **Manual test checklist** (run the real app, simulate bedtime by setting
   the time 1 minute ahead) — coach screen appears, all 4 choices work,
   enforcement still fires on no-answer.

---

## 10. Build order (small steps, each verified)

1. `coach/store.py` + `schemas.py` — database + tests
2. `coach/activity.py` + `classifier.py` — program name + guessing + tests
3. `coach/recommender.py` + `explainer.py` — scoring + reasons + tests
4. `pages/coach_page.py` — the bedtime screen, wired into `enforcer.py`
   (replaces what `show_reason_prompt()` opens; `ReasonPage` stays as
   fallback)
5. Feedback popup + replans + outcomes
6. Settings sections + data controls (export/import/delete)
7. `coach/patterns.py` — history learning feeding back into recommendations
8. Polish: keyboard navigation, manual test pass, version bump to 1.4.0

Each step runs both test suites before moving on. All work on `agent-dev`.

---

## 11. What we deliberately are NOT building (v1.1+)

- Dashboard views (v1.1)
- Cloud sync, external AI, reading documents/messages (v2+)
- Any keystroke/screenshot/content capture (never)
