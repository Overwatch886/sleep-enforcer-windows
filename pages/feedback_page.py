"""The next-day feedback popup (design.md, section 6).

Non-blocking Toplevel, skippable. Auto-detects what it can (PC resume
time) but the user's click is what gets recorded (locked decision).
"""
import tkinter as tk
from tkinter import ttk

from coach.patterns import Patterns

OUTCOME_OPTIONS = (
    ("finished", "✅ Finished"),
    ("postponed", "📆 Postponed"),
    ("overslept", "😴 Overslept"),
    ("late", "⏰ Was late"),
    ("regretted", "😕 Regretted staying up"),
    ("rec_wrong", "❌ Advice was wrong"),
    ("skipped", "Skip"),
)


class FeedbackPopup(tk.Toplevel):
    def __init__(self, controller, event):
        super().__init__(controller)
        self.controller = controller
        self.event = event
        self.title("How did it go?")
        self.configure(bg="#0f172a")
        self.resizable(False, False)
        self.attributes("-topmost", True)

        w, h = 460, 340
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        tk.Label(self, text="🌙 Last night's choice", font=("Segoe UI", 14, "bold"),
                 bg="#0f172a", fg="#3b82f6").pack(pady=(16, 6))

        # What happened, in one line
        choice = event.choice or "?"
        task_desc = (event.task.description if event.task and event.task.description
                     else (event.task.category if event.task else "unknown"))
        tk.Label(self,
                 text=f"You chose: {choice} — {task_desc}",
                 font=("Segoe UI", 11), bg="#0f172a", fg="#f8fafc").pack(pady=(0, 8))

        # Auto-detected info (fallback signal only — the click is what counts)
        auto_text = self._auto_detected_text()
        if auto_text:
            tk.Label(self, text=auto_text, font=("Segoe UI", 10),
                     bg="#0f172a", fg="#94a3b8", wraplength=400).pack(pady=(0, 4))

        tk.Label(self, text="What happened?", font=("Segoe UI", 11, "bold"),
                 bg="#0f172a", fg="#cbd5e1").pack(pady=(8, 6))

        # Outcome buttons in two columns
        grid = tk.Frame(self, bg="#0f172a")
        grid.pack(pady=(0, 10))
        for i, (value, label) in enumerate(OUTCOME_OPTIONS):
            btn = ttk.Button(grid, text=label,
                             command=lambda v=value: self._report(v))
            btn.grid(row=i // 2, column=i % 2, padx=6, pady=4, ipadx=10, sticky="ew")
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        # Open replanned tasks — done?
        self._replan_rows(controller.store.open_replans())

        self.protocol("WM_DELETE_WINDOW", self._skip)
        self.lift()
        self.focus_force()

    def _auto_detected_text(self) -> str:
        try:
            resume = Patterns(self.controller.store).pc_resume_time_yesterday()
            if resume:
                return f"(PC came back on around {resume.strftime('%H:%M')} — auto-detected)"
        except Exception as e:
            print(f"[DEBUG] Auto-detect failed: {e}")
        return ""

    def _replan_rows(self, replans):
        if not replans:
            return
        tk.Label(self, text="Replanned tasks — done?", font=("Segoe UI", 10, "bold"),
                 bg="#0f172a", fg="#94a3b8").pack(pady=(6, 2))
        for rp in replans[:3]:
            row = tk.Frame(self, bg="#0f172a")
            row.pack(fill="x", padx=20, pady=2)
            tk.Label(row, text=rp["title"], font=("Segoe UI", 10),
                     bg="#0f172a", fg="#f8fafc").pack(side="left")
            ttk.Button(row, text="Yes",
                       command=lambda r=rp: self._replan_done(r, True)).pack(side="right", padx=2)
            ttk.Button(row, text="Not yet",
                       command=lambda r=rp: self._replan_done(r, False)).pack(side="right")

    def _replan_done(self, rp, done: bool):
        try:
            self.controller.store.mark_replan_done(rp["id"], done)
        except Exception as e:
            print(f"[DEBUG] mark_replan_done failed: {e}")
        for w in self.winfo_children():
            pass  # keep it simple: buttons stay, user can still report outcome

    def _report(self, value: str):
        try:
            auto = self._auto_detected_text().strip("()")
            self.controller.store.save_outcome(
                self.event.id, reported=value, auto_detected=auto)
            print(f"[DEBUG] Outcome saved: {value} for event {self.event.id}")
        except Exception as e:
            print(f"[DEBUG] save_outcome failed: {e}")
        self.destroy()

    def _skip(self):
        self._report("skipped")
