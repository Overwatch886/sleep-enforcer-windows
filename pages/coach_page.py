"""The bedtime coach screen (design.md, section 6).

Display-only: it shows the classifier's guess, collects the task tags,
shows the recommendation + comparison, and hands the user's choice to the
controller (enforcer.py). All thinking happened in coach/ already.

The controller builds a CoachSession (plain data) and calls
start_session() before raising this frame.
"""
import tkinter as tk
from tkinter import ttk

from coach.explainer import build_comparison, build_explanation, choice_label
from coach.schemas import CATEGORIES, Recommendation, TaskDetails

DURATION_OPTIONS = (15, 30, 45, 60, 90, 120)


class CoachSession:
    """Plain data bundle the controller prepares for one bedtime session."""

    def __init__(self, program_name: str, classification,
                 extension_available: bool, extension_minutes: int):
        self.program_name = program_name
        self.classification = classification      # Classification
        self.extension_available = extension_available
        self.extension_minutes = extension_minutes
        self.recommendation: Recommendation = None
        self.task: TaskDetails = TaskDetails(source="user")
        self.event_id = None


class CoachPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent, bg="#0f172a")
        self.controller = controller
        self.session = None
        self._grace_after_id = None

        # Scrollable content on a dark card
        outer = tk.Frame(self, bg="#0f172a")
        outer.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(outer, bg="#0f172a", highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical",
                                  command=self.canvas.yview)
        self.card = tk.Frame(self.canvas, bg="#1e293b",
                             highlightbackground="#334155", highlightthickness=1)

        self.card.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.card, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self._build_header()
        self._build_guess_row()
        self._build_questions()
        self._build_recommendation()
        self._build_comparison()
        self._build_buttons()
        self._build_grace_label()

    # --- construction helpers ---

    def _build_header(self):
        header = tk.Frame(self.card, bg="#1e293b")
        header.pack(fill="x", padx=20, pady=(16, 4))
        self.title_label = tk.Label(
            header, text="🌙 Bedtime — let's decide together",
            font=("Segoe UI", 16, "bold"), bg="#1e293b", fg="#f8fafc")
        self.title_label.pack()
        self.sub_label = tk.Label(
            header, text="", font=("Segoe UI", 10),
            bg="#1e293b", fg="#94a3b8")
        self.sub_label.pack()

    def _build_guess_row(self):
        row = tk.Frame(self.card, bg="#1e293b")
        row.pack(fill="x", padx=20, pady=(8, 0))
        self.guess_label = tk.Label(
            row, text="", font=("Segoe UI", 10), bg="#1e293b",
            fg="#cbd5e1", wraplength=520, justify="left", anchor="w")
        self.guess_label.pack(side="left", fill="x", expand=True)
        fix_btn = ttk.Button(row, text="✏️ Fix",
                             command=self._on_fix_guess)
        fix_btn.pack(side="right")

    def _build_questions(self):
        section = tk.Frame(self.card, bg="#1e293b")
        section.pack(fill="x", padx=20, pady=(10, 0))

        tk.Label(section, text="What's going on?", font=("Segoe UI", 10, "bold"),
                 bg="#1e293b", fg="#94a3b8").pack(anchor="w")
        cat_row = tk.Frame(section, bg="#1e293b")
        cat_row.pack(fill="x", pady=(2, 8))
        self.category_combo = ttk.Combobox(
            cat_row, values=list(CATEGORIES), state="readonly", width=22)
        self.category_combo.pack(side="left")

        def scale_row(parent, label, from_, to, variable):
            frame = tk.Frame(parent, bg="#1e293b")
            frame.pack(fill="x", pady=2)
            tk.Label(frame, text=label, font=("Segoe UI", 10),
                     bg="#1e293b", fg="#94a3b8", width=12, anchor="w").pack(side="left")
            ttk.Scale(frame, from_=from_, to=to, variable=variable,
                      command=lambda v: variable.set(round(float(v)))).pack(
                side="left", fill="x", expand=True, padx=8)
            value_label = tk.Label(frame, textvariable=variable, width=2,
                                   bg="#1e293b", fg="#f8fafc",
                                   font=("Segoe UI", 10, "bold"))
            value_label.pack(side="right")
            return frame

        import tkinter.ttk as ttk_mod  # noqa: F401 (kept for clarity)
        self.urgency_var = tk.IntVar(value=3)
        self.importance_var = tk.IntVar(value=3)
        scale_row(section, "Urgency (1-5)", 1, 5, self.urgency_var)
        scale_row(section, "Importance (1-5)", 1, 5, self.importance_var)

        dur_row = tk.Frame(section, bg="#1e293b")
        dur_row.pack(fill="x", pady=(8, 0))
        tk.Label(dur_row, text="Needs about:", font=("Segoe UI", 10),
                 bg="#1e293b", fg="#94a3b8").pack(side="left")
        self.duration_combo = ttk.Combobox(
            dur_row, values=[f"{m} min" for m in DURATION_OPTIONS],
            state="readonly", width=10)
        self.duration_combo.current(1)  # 30 min default
        self.duration_combo.pack(side="left", padx=8)
        tk.Label(dur_row, text="(optional note below)", font=("Segoe UI", 9),
                 bg="#1e293b", fg="#64748b").pack(side="left", padx=6)

        self.note_entry = tk.Entry(section, font=("Segoe UI", 10),
                                   bg="#0f172a", fg="#f8fafc",
                                   insertbackground="#f8fafc", relief="solid",
                                   bd=1, highlightthickness=1,
                                   highlightbackground="#334155")
        self.note_entry.pack(fill="x", pady=(8, 12), ipady=3)

    def _build_recommendation(self):
        section = tk.Frame(self.card, bg="#0b1220",
                           highlightbackground="#3b82f6", highlightthickness=1)
        section.pack(fill="x", padx=20, pady=(10, 0))
        self.rec_title = tk.Label(
            section, text="", font=("Segoe UI", 13, "bold"),
            bg="#0b1220", fg="#3b82f6")
        self.rec_title.pack(pady=(10, 4))
        self.rec_text = tk.Label(
            section, text="", font=("Segoe UI", 10), bg="#0b1220",
            fg="#cbd5e1", wraplength=520, justify="left")
        self.rec_text.pack(padx=14, pady=(0, 10), fill="x")

    def _build_comparison(self):
        self.compare_label = tk.Label(
            self.card, text="", font=("Segoe UI", 10), bg="#1e293b",
            fg="#94a3b8", wraplength=540, justify="left", anchor="w")
        self.compare_label.pack(fill="x", padx=20, pady=(10, 0))

    def _build_buttons(self):
        row = tk.Frame(self.card, bg="#1e293b")
        row.pack(pady=12)
        self.sleep_btn = ttk.Button(row, text="😴 Sleep now",
                                    command=lambda: self._submit("sleep"))
        self.sleep_btn.pack(side="left", padx=4, ipadx=8)
        self.replan_btn = ttk.Button(row, text="📅 Replan",
                                     command=lambda: self._submit("replan"))
        self.replan_btn.pack(side="left", padx=4, ipadx=8)
        self.continue_btn = ttk.Button(row, text="▶ Continue",
                                       command=lambda: self._submit("continue"))
        self.continue_btn.pack(side="left", padx=4, ipadx=8)
        self.break_btn = ttk.Button(row, text="☕ Break first",
                                    command=lambda: self._submit("break"))
        self.break_btn.pack(side="left", padx=4, ipadx=8)

        skip_row = tk.Frame(self.card, bg="#1e293b")
        skip_row.pack(pady=(0, 14))
        skip_btn = ttk.Button(skip_row, text="Skip questions →",
                              command=self._on_skip)
        skip_btn.pack()

    def _build_grace_label(self):
        self.grace_label = tk.Label(
            self.card, text="", font=("Segoe UI", 10, "bold"),
            bg="#1e293b", fg="#f59e0b")
        self.grace_label.pack(pady=(0, 12))

    # --- runtime ---

    def start_session(self, session: CoachSession):
        """Called by the controller right before showing this page."""
        self.session = session

        self.title_label.config(
            text=f"🌙 It's {self.controller.shutdown_time_str} — bedtime")
        self.sub_label.config(
            text=f"Schedule: wake at {self.controller.wake_time_str} · "
                 f"extension: {session.extension_minutes} min"
                 + ("" if session.extension_available else " (already used tonight)"))

        # Guess row
        if session.program_name:
            guess = session.classification
            self.guess_label.config(
                text=f"Looks like you're in {session.program_name} → "
                     f"{guess.category} "
                     f"(confidence: {guess.confidence_label}). {guess.evidence}")
        else:
            self.guess_label.config(
                text="I couldn't see which program is in front.")

        # Pre-fill the category with the guess, but the user always confirms.
        self.category_combo.set(session.classification.category)
        self.urgency_var.set(3)
        self.importance_var.set(3)
        self.duration_combo.current(1)
        self.note_entry.delete(0, "end")

        # Recommendation + comparison (re-rendered as the user changes tags)
        self._render_recommendation()
        self._update_grace_label()

        # Live-update the recommendation as the user adjusts their answers.
        self.category_combo.bind("<<ComboboxSelected>>",
                                 lambda e: self._refresh_from_tags())
        self.duration_combo.bind("<<ComboboxSelected>>",
                                 lambda e: self._refresh_from_tags())
        for var in (self.urgency_var, self.importance_var):
            var.trace_add("write", lambda *_: self._refresh_from_tags())

    def _refresh_from_tags(self):
        """Re-think the recommendation with the user's current answers."""
        if self.session is None or self.controller.recommender is None:
            return
        self._collect_task()
        session = self.session
        session.recommendation = self.controller.recommender.recommend(
            session.task,
            extension_available=session.extension_available,
            extension_minutes=session.extension_minutes,
            strict_break_mode=self.controller.strict_break_mode,
        )
        session.recommendation.explanation = build_explanation(
            session.recommendation, session.task, session.extension_minutes)
        self._render_recommendation()

    def _render_recommendation(self):
        rec = self.session.recommendation
        self.rec_title.config(
            text=f"My recommendation: {choice_label(rec.recommended_choice)}")
        self.rec_text.config(text=rec.explanation)

        comparison = build_comparison(
            self.session.task, self.session.extension_minutes,
            self.session.extension_available)
        continue_lines = "\n".join(f"  • {l}" for l in comparison["continue"])
        sleep_lines = "\n".join(f"  • {l}" for l in comparison["sleep"])
        self.compare_label.config(
            text=f"If you continue:\n{continue_lines}\n\n"
                 f"If you sleep and replan:\n{sleep_lines}")

        # Disable Continue when tonight's extension is spent — say why.
        if self.session.extension_available:
            self.continue_btn.state(["!disabled"])
            self.continue_btn.config(text=f"▶ Continue {self.session.extension_minutes}m")
        else:
            self.continue_btn.state(["disabled"])
            self.continue_btn.config(text="▶ Continue (used)")

    def _update_grace_label(self):
        """Show the remaining grace time; existing timeout still applies."""
        remaining = getattr(self.controller, "grace_seconds_left", None)
        if remaining is None:
            self.grace_label.config(text="No answer when the timer ends → sleep flow starts.")
            return
        m, s = divmod(max(0, int(remaining)), 60)
        self.grace_label.config(
            text=f"⏳ Time to decide: {m}:{s:02d} — after that, the sleep flow starts.")
        self._grace_after_id = self.after(1000, self._update_grace_label)

    # --- events ---

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _collect_task(self) -> TaskDetails:
        task = self.session.task
        task.category = self.category_combo.get() or "unknown"
        task.urgency = int(self.urgency_var.get())
        task.importance = int(self.importance_var.get())
        task.est_minutes = DURATION_OPTIONS[self.duration_combo.current()]
        task.description = self.note_entry.get().strip()
        task.source = "user"
        return task

    def _on_fix_guess(self):
        """One-click fix: current program → chosen category, also learns."""
        guessed = self.session.classification
        current_choice = self.category_combo.get()
        if current_choice and current_choice != guessed.category:
            # The user already changed the dropdown — treat that as the fix.
            self.controller.coach_fix_guess(
                self.session, current_choice, make_rule=False)
            self.guess_label.config(
                text=f"Noted — {self.session.program_name} counts as "
                     f"{current_choice}. I'll remember that.")
        else:
            self.controller.show_custom_warning(
                "Fix the guess",
                "Pick the right category in the 'What's going on?' dropdown "
                "first, then press ✏️ Fix again.")

    def _on_skip(self):
        """Skip questions → straight to the choice buttons, category unknown."""
        self.category_combo.set("unknown")
        self.guess_label.config(text="Okay — no questions. Just pick below.")
        self.session.task.category = "unknown"
        self.session.task.source = "user"

    def _submit(self, choice: str):
        if choice == "continue" and not self.session.extension_available:
            return
        self._collect_task()
        self.controller.coach_choose(self.session, choice)

    def stop_timers(self):
        if self._grace_after_id:
            try:
                self.after_cancel(self._grace_after_id)
            except Exception:
                pass
            self._grace_after_id = None
