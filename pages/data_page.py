"""Data & goals controls section (design.md, section 8; plan.md FR-11).

A scrollable settings section: coaching options, goals, category rules,
and data controls (view collected / export / import / delete).
Display-only — all persistence goes through the Store.
"""
import json
import tkinter as tk
from tkinter import ttk, filedialog

from coach.schemas import CATEGORIES


class DataPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent, bg="#0f172a")
        self.controller = controller

        # Scrollable area
        outer = tk.Frame(self, bg="#0f172a")
        outer.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(outer, bg="#0f172a", highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=self.canvas.yview)
        content = tk.Frame(self.canvas, bg="#0f172a")
        content.bind("<Configure>",
                     lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=content, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(
            int(-1 * (e.delta / 120)), "units"))

        # Header + back
        header = tk.Frame(content, bg="#0f172a")
        header.pack(fill="x", pady=(15, 5))
        tk.Label(header, text="🧠 Coach Settings & Data", font=("Segoe UI", 18, "bold"),
                 bg="#0f172a", fg="#3b82f6").pack()
        ttk.Button(header, text="← Back to Home",
                   command=lambda: controller.show_frame("StartupPage")).pack(pady=6)

        self._build_coaching_section(content)
        self._build_goals_section(content)
        self._build_rules_section(content)
        self._build_data_section(content)

    # --- Coaching ---

    def _build_coaching_section(self, parent):
        section = self._section(parent, "Coaching")
        row = tk.Frame(section, bg="#1e293b")
        row.pack(fill="x", padx=12, pady=6)

        self.watch_var = tk.BooleanVar(value=self.controller.coach_watch_programs)
        ttk.Checkbutton(row, text="Let the app see which program is in front at bedtime "
                                  "(program name only — never content)",
                        variable=self.watch_var).pack(anchor="w", pady=2)

        self.coach_var = tk.BooleanVar(value=self.controller.coaching_enabled)
        ttk.Checkbutton(row, text="Show the coach screen at bedtime "
                                  "(off = old reason prompt)",
                        variable=self.coach_var).pack(anchor="w", pady=2)

        intensity_row = tk.Frame(section, bg="#1e293b")
        intensity_row.pack(fill="x", padx=12, pady=(2, 10))
        tk.Label(intensity_row, text="Coaching intensity:", bg="#1e293b",
                 fg="#94a3b8", font=("Segoe UI", 10)).pack(side="left")
        self.intensity_combo = ttk.Combobox(
            intensity_row, values=["gentle", "normal", "firm"],
            state="readonly", width=10)
        self.intensity_combo.set(self.controller.coach_intensity)
        self.intensity_combo.pack(side="left", padx=8)

        ttk.Button(section, text="💾 Save Coaching Settings",
                   command=self._save_coaching).pack(pady=(4, 12))

    def _save_coaching(self):
        c = self.controller
        c.coach_watch_programs = self.watch_var.get()
        c.coaching_enabled = self.coach_var.get()
        c.coach_intensity = self.intensity_combo.get()
        c.save_persistent_settings()
        self.controller.show_custom_warning(
            "Saved", "Coaching settings saved.")

    # --- Goals ---

    def _build_goals_section(self, parent):
        section = self._section(parent, "Your goals & principles")
        self.goals_listbox = tk.Listbox(section, bg="#0f172a", fg="#f8fafc",
                                        selectbackground="#3b82f6",
                                        highlightthickness=1,
                                        highlightbackground="#334155",
                                        height=6)
        self.goals_listbox.pack(fill="x", padx=12, pady=6)

        entry_row = tk.Frame(section, bg="#1e293b")
        entry_row.pack(fill="x", padx=12, pady=(0, 4))
        self.goal_entry = tk.Entry(entry_row, font=("Segoe UI", 10), bg="#0f172a",
                                   fg="#f8fafc", insertbackground="#f8fafc",
                                   relief="solid", bd=1)
        self.goal_entry.pack(side="left", fill="x", expand=True, ipady=3, padx=(0, 6))
        ttk.Button(entry_row, text="Add", command=self._add_goal).pack(side="left")

        btn_row = tk.Frame(section, bg="#1e293b")
        btn_row.pack(pady=(4, 12))
        ttk.Button(btn_row, text="Toggle active",
                   command=self._toggle_goal).pack(side="left", padx=4)
        ttk.Button(btn_row, text="Delete",
                   command=self._delete_goal).pack(side="left", padx=4)
        self._refresh_goals()

    def _refresh_goals(self):
        self.goals_listbox.delete(0, "end")
        for g in self.controller.store.all_goals():
            marker = "✓" if g["active"] else "✗"
            label = f"{marker} {g['text']}" + ("  (starter)" if g["builtin"] else "")
            self.goals_listbox.insert("end", label)

    def _selected_goal(self):
        sel = self.goals_listbox.curselection()
        if not sel:
            return None
        goals = self.controller.store.all_goals()
        visible = [g for g in goals]  # same order as listbox
        return visible[sel[0]] if sel[0] < len(visible) else None

    def _add_goal(self):
        text = self.goal_entry.get().strip()
        if text:
            self.controller.store.add_goal(text)
            self.goal_entry.delete(0, "end")
            self._refresh_goals()

    def _toggle_goal(self):
        g = self._selected_goal()
        if g:
            self.controller.store.set_goal_active(g["id"], not g["active"])
            self._refresh_goals()

    def _delete_goal(self):
        g = self._selected_goal()
        if g:
            self.controller.store.delete_goal(g["id"])
            self._refresh_goals()

    # --- Category rules ---

    def _build_rules_section(self, parent):
        section = self._section(parent, "Program → category rules")
        tk.Label(section, text="Teach the app what your programs count as. "
                               "Your rules always win.",
                 font=("Segoe UI", 10), bg="#1e293b", fg="#94a3b8").pack(
            anchor="w", padx=12, pady=(0, 4))

        self.rules_tree = ttk.Treeview(section, columns=("program", "category"),
                                       show="headings", height=6)
        self.rules_tree.heading("program", text="Program")
        self.rules_tree.heading("category", text="Category")
        self.rules_tree.column("program", width=220)
        self.rules_tree.column("category", width=120)
        self.rules_tree.pack(fill="x", padx=12, pady=6)

        add_row = tk.Frame(section, bg="#1e293b")
        add_row.pack(fill="x", padx=12, pady=(0, 4))
        self.rule_program_entry = tk.Entry(add_row, font=("Segoe UI", 10),
                                           bg="#0f172a", fg="#f8fafc",
                                           insertbackground="#f8fafc",
                                           relief="solid", bd=1, width=18)
        self.rule_program_entry.pack(side="left", ipady=3, padx=(0, 6))
        self.rule_category_combo = ttk.Combobox(add_row, values=list(CATEGORIES),
                                                state="readonly", width=12)
        self.rule_category_combo.set("study")
        self.rule_category_combo.pack(side="left", padx=(0, 6))
        ttk.Button(add_row, text="Add rule", command=self._add_rule).pack(side="left")

        ttk.Button(section, text="Remove selected rule",
                   command=self._remove_rule).pack(pady=(4, 12))
        self._refresh_rules()

    def _refresh_rules(self):
        for i in self.rules_tree.get_children():
            self.rules_tree.delete(i)
        for r in self.controller.store.user_category_rules():
            self.rules_tree.insert("", "end", values=(r["program_name"], r["category"]))

    def _add_rule(self):
        program = self.rule_program_entry.get().strip().lower()
        category = self.rule_category_combo.get()
        if program:
            self.controller.store.upsert_category_rule(program, category)
            self.rule_program_entry.delete(0, "end")
            self._refresh_rules()

    def _remove_rule(self):
        sel = self.rules_tree.selection()
        if sel:
            program = self.rules_tree.item(sel[0])["values"][0]
            self.controller.store.remove_category_rule(str(program))
            self._refresh_rules()

    # --- Data controls (FR-11) ---

    def _build_data_section(self, parent):
        section = self._section(parent, "Your data")
        tk.Label(section, text="Everything is stored only on this PC, in "
                               "%LOCALAPPDATA%\\SleepEnforcer.",
                 font=("Segoe UI", 10), bg="#1e293b", fg="#94a3b8",
                 wraplength=480, justify="left").pack(anchor="w", padx=12, pady=(0, 6))

        btn_row = tk.Frame(section, bg="#1e293b")
        btn_row.pack(pady=(0, 12))
        ttk.Button(btn_row, text="View collected",
                   command=self._view_data).pack(side="left", padx=4)
        ttk.Button(btn_row, text="Export",
                   command=self._export_data).pack(side="left", padx=4)
        ttk.Button(btn_row, text="Import",
                   command=self._import_data).pack(side="left", padx=4)
        self.delete_btn = ttk.Button(btn_row, text="Delete history",
                                     command=self._delete_history)
        self.delete_btn.pack(side="left", padx=4)

    def _view_data(self):
        data = self.controller.store.export_all()
        n_events = len(data["events"])
        n_outcomes = len(data["outcomes"])
        n_rules = len(data["category_rules"])
        self.controller.show_custom_warning(
            "What's collected",
            f"Collected so far:\n\n"
            f"• {n_events} bedtime events\n"
            f"• {n_outcomes} outcome reports\n"
            f"• {n_rules} category rules\n"
            f"• program names (never content)\n"
            f"• task tags you entered")

    def _export_data(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON export", "*.json")],
            initialfile="sleep_enforcer_data.json")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.controller.store.export_all(), f, indent=2)
        self.controller.show_custom_warning("Exported", f"Data saved to:\n{path}")

    def _import_data(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON export", "*.json")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.controller.store.import_all(data)
            self.controller.show_custom_warning("Imported", "Data restored.")
            self._refresh_goals()
            self._refresh_rules()
        except Exception as e:
            self.controller.show_custom_warning("Import failed", f"Could not read that file:\n{e}")

    def _delete_history(self):
        """Two-step confirm, non-blocking (agentrules rule 4)."""
        if getattr(self, "_confirm_delete", False):
            self.controller.store.delete_history()
            self._confirm_delete = False
            self.delete_btn.config(text="Delete history")
            self.controller.show_custom_warning("Deleted", "History deleted.")
            return
        self._confirm_delete = True
        self.delete_btn.config(text="⚠️ Click again to delete")
        self.after(10000, lambda: (setattr(self, "_confirm_delete", False),
                                   self.delete_btn.config(text="Delete history")))
        self.controller.show_custom_warning(
            "Delete history?",
            "This removes all events, outcomes and learned patterns.\n"
            "Goals and rules are kept.\n\n"
            "Click 'Delete history' again to confirm.")

    # --- helper ---

    @staticmethod
    def _section(parent, title):
        section = tk.Frame(parent, bg="#1e293b",
                           highlightbackground="#334155", highlightthickness=1)
        section.pack(fill="x", padx=20, pady=(10, 5))
        tk.Label(section, text=title, font=("Segoe UI", 12, "bold"),
                 bg="#1e293b", fg="#3b82f6").pack(anchor="w", padx=12, pady=(12, 8))
        return section
