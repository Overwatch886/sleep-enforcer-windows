import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
import threading
import time
from datetime import datetime, timedelta, time as datetime_time
import os
import json
import subprocess
import sys
import tempfile
from PIL import Image, ImageTk
import pystray
from pystray import MenuItem as item
import psutil
import atexit

class DualLogger:
    """Redirects stdout/stderr to both the terminal console (if available) and a persistent log file."""
    def __init__(self, filepath, terminal_stream):
        self.terminal = terminal_stream
        self.filepath = filepath
        try:
            self.log = open(self.filepath, "a", encoding="utf-8")
        except Exception:
            self.log = None
        
    def write(self, message):
        if self.terminal is not None:
            try:
                self.terminal.write(message)
            except Exception:
                pass
        if self.log is not None:
            try:
                self.log.write(message)
                self.log.flush()
            except Exception:
                pass
        
    def flush(self):
        if self.terminal is not None:
            try:
                self.terminal.flush()
            except Exception:
                pass
        if self.log is not None:
            try:
                self.log.flush()
            except Exception:
                pass
    
    def close(self):
        if self.terminal is not None:
            try:
                self.terminal.close()
            except Exception:
                pass
        if self.log is not None:
            try:
                self.log.close()
            except Exception:
                pass



# Relative File Resolver to Help Find Other Non-python resources
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class SingleInstance:
    """This class ensures that only one instance of our sleep enforcer app is running"""
    def __init__(self):
        self.lockfile = os.path.join(tempfile.gettempdir(), 'sleep_enforcer.lock')
        
        if os.path.exists(self.lockfile):
            try:
                with open(self.lockfile, 'r') as f:
                    pid = int(f.read().strip())
                if psutil.pid_exists(pid):
                    proc = psutil.Process(pid)
                    cmdline = [arg.lower() for arg in proc.cmdline()]
                    is_our_app = False
                    
                    if 'sleep_enforcer' in proc.name().lower():
                        is_our_app = True
                    elif 'python' in proc.name().lower():
                        # Make sure we don't block other python apps, only our sleep enforcer
                        if any('sleep_enforcer' in arg for arg in cmdline):
                            is_our_app = True
                            
                    if is_our_app:
                        print("Sleep Enforcer is already running!")
                        sys.exit(1)
                    else:
                        print(f"[INFO] Stale lock file found (PID {pid} belongs to '{proc.name()}'). Overwriting.")
            except (OSError, ValueError, psutil.NoSuchProcess, psutil.AccessDenied) as e:
                print(f"[INFO] Clearing invalid lock file: {e}")
        try:
            with open(self.lockfile, 'w') as f:
                f.write(str(os.getpid()))
        except IOError as e:
            print(f"[ERROR] Could not write lock file {e}")


# Register exit cleanup hook for lock file
def cleanup_lockfile():
    lockfile = os.path.join(tempfile.gettempdir(), 'sleep_enforcer.lock')
    if os.path.exists(lockfile):
        try:
            os.remove(lockfile)
            print("[DEBUG] Cleaned up lock file on exit.")
        except Exception:
            pass

atexit.register(cleanup_lockfile)


# --- "Page" Frames (Views) ---

class StartupPage(tk.Frame):
    """
    This is the main "dashboard" page.
    """
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent, bg="#0f172a")
        self.controller = controller

        # Header
        header = tk.Frame(self, bg=self['bg'])
        header.pack(fill='x', pady=(20, 10))
        title = tk.Label(header, text="💤 Healthy Sleep Enforcer", font=("Segoe UI", 18, "bold"), bg=self['bg'], fg="#3b82f6")
        title.pack()
        subtitle = tk.Label(header, text="Sleep tracking active", font=("Segoe UI", 10), bg=self['bg'], fg="#94a3b8")
        subtitle.pack()

        # Status card
        card = tk.Frame(self, bg="#1e293b", highlightbackground="#334155", highlightthickness=1)
        card.pack(padx=20, pady=15, fill='x')
        
        status_text = f'''⏰ Warning at: {self.controller.warning_time_str}
🛑 Bedtime at: {self.controller.shutdown_time_str}
🌞 Wake Time at: {self.controller.wake_time_str}'''
        
        self.status_label = tk.Label(card, text=status_text, font=("Segoe UI", 11), bg="#1e293b", fg="#f8fafc", justify="left")
        self.status_label.pack(padx=20, pady=16)

        # Actions area
        actions = tk.Frame(self, bg=self['bg'])
        actions.pack(pady=20)
        settings_btn = ttk.Button(actions, text="⚙️ Settings", command=lambda: controller.show_frame("SettingsPage"))
        settings_btn.pack(ipadx=12, ipady=8)

    def update_status(self):
        """Updates the time labels when called by the controller."""
        status_text = f'''⏰ Warning at: {self.controller.warning_time_str}
🛑 Bedtime at: {self.controller.shutdown_time_str}
🌞 Wake Time at: {self.controller.wake_time_str}'''
        self.status_label.config(text=status_text)


class SettingsPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent, bg="#0f172a")
        self.controller = controller

        # ===== HEADER FRAME =====
        header = tk.Frame(self, bg="#0f172a")
        header.pack(fill='x', padx=0, pady=0)
        
        title = tk.Label(header, text="⚙️ Settings", font=("Segoe UI", 18, "bold"), bg="#0f172a", fg="#3b82f6")
        title.pack(pady=(15, 10))

        # ===== FOOTER FRAME =====
        footer = tk.Frame(self, bg="#0f172a", borderwidth=0)
        footer.pack(fill='x', padx=0, pady=0, side='bottom')
        
        footer_content = tk.Frame(footer, bg="#0f172a")
        footer_content.pack(padx=15, pady=12)
        
        save_btn = ttk.Button(footer_content, text="💾 Save Settings", command=lambda: controller.save_settings())
        save_btn.pack(side='left', padx=(0, 10))
        
        back_btn = ttk.Button(footer_content, text="← Back to Home", command=lambda: controller.show_frame("StartupPage"))
        back_btn.pack(side='left')

        # ===== SCROLLABLE CONTENT AREA =====
        canvas_frame = tk.Frame(self, bg="#0f172a")
        canvas_frame.pack(fill='both', expand=True, padx=0, pady=0)

        self.canvas = tk.Canvas(canvas_frame, bg="#0f172a", highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient='vertical', command=self.canvas.yview)
        scrollable_frame = tk.Frame(self.canvas, bg="#0f172a")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        self.canvas.bind_all('<MouseWheel>', lambda e: self._on_mousewheel(e))

        # Time options
        time_options = [f"{h:02d}:{m:02d}" for h in range(24) for m in range(0, 60, 15)]
        
        # Section: Sleep Schedule
        schedule_section = tk.Frame(scrollable_frame, bg="#1e293b", highlightbackground="#334155", highlightthickness=1)
        schedule_section.pack(fill='x', padx=20, pady=(10, 10))

        schedule_title = tk.Label(schedule_section, text="Sleep Schedule", font=("Segoe UI", 12, "bold"), bg="#1e293b", fg="#3b82f6")
        schedule_title.pack(anchor='w', padx=12, pady=(12, 8))

        # Warning time
        warning_container = tk.Frame(schedule_section, bg="#1e293b")
        warning_container.pack(fill='x', padx=12, pady=6)
        warning_label = tk.Label(warning_container, text="⏰ Warning Time", bg="#1e293b", fg="#94a3b8", font=("Segoe UI", 10, "bold"))
        warning_label.pack(anchor='w')
        self.warning_combo = ttk.Combobox(warning_container, values=time_options, width=25, state='normal')
        self.warning_combo.set(controller.warning_time_str)
        self.warning_combo.pack(anchor='w', pady=(4, 0))
        self.warning_combo.bind('<KeyRelease>', lambda e: self._filter_options(e, self.warning_combo, time_options))

        # Shutdown time
        shutdown_container = tk.Frame(schedule_section, bg="#1e293b")
        shutdown_container.pack(fill='x', padx=12, pady=6)
        shutdown_label = tk.Label(shutdown_container, text="🌙 Bedtime", bg="#1e293b", fg="#ef4444", font=("Segoe UI", 10, "bold"))
        shutdown_label.pack(anchor='w')
        self.shutdown_combo = ttk.Combobox(shutdown_container, values=time_options, width=25, state='normal')
        self.shutdown_combo.set(controller.shutdown_time_str)
        self.shutdown_combo.pack(anchor='w', pady=(4, 0))
        self.shutdown_combo.bind('<KeyRelease>', lambda e: self._filter_options(e, self.shutdown_combo, time_options))

        # Wake time
        wake_container = tk.Frame(schedule_section, bg="#1e293b")
        wake_container.pack(fill='x', padx=12, pady=(6, 12))
        self.waketime_label = tk.Label(wake_container, text="🌞 Wake Time", fg="#10b981", font=("Segoe UI", 10, "bold"), bg="#1e293b")
        self.waketime_label.pack(anchor='w')
        self.waketime_combo = ttk.Combobox(wake_container, values=time_options, width=25, state='normal')
        self.waketime_combo.set(controller.wake_time_str)
        self.waketime_combo.pack(anchor='w', pady=(4, 0))
        self.waketime_combo.bind('<KeyRelease>', lambda e: self._filter_options(e, self.waketime_combo, time_options))

        # Section: Behavior
        behavior_section = tk.Frame(scrollable_frame, bg="#1e293b", highlightbackground="#334155", highlightthickness=1)
        behavior_section.pack(fill='x', padx=20, pady=(5, 15))

        behavior_title = tk.Label(behavior_section, text="Behavior", font=("Segoe UI", 12, "bold"), bg="#1e293b", fg="#3b82f6")
        behavior_title.pack(anchor='w', padx=12, pady=(12, 8))

        # Strict break mode checkbox
        self.strict_var = tk.BooleanVar(value=controller.strict_break_mode)
        strict_container = tk.Frame(behavior_section, bg="#1e293b")
        strict_container.pack(fill='x', padx=12, pady=(8, 12))
        strict_check = ttk.Checkbutton(strict_container, text="Enable mandatory 5-minute break", variable=self.strict_var)
        strict_check.pack(anchor='w')


    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling on the canvas."""
        if self.canvas.winfo_containing(event.x_root, event.y_root) == self.canvas:
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _filter_options(self, event, combo, all_options):
        """Filter options using 'starts with' logic and maintain cursor position."""
        val = combo.get()
        pos = combo.index(tk.INSERT)

        if val == '':
            filtered = all_options
        else:
            filtered = [item for item in all_options 
                        if item.startswith(val) or (len(val) == 1 and item.startswith('0' + val))]
        
        combo['values'] = filtered
        combo.icursor(pos)

        if event.keysym not in ('Return', 'Tab', 'Escape', 'Up', 'Down', 'BackSpace', 'Left', 'Right'):
            if filtered:
                combo.event_generate('<Down>')


class ReasonPage(tk.Frame):
    """
    This is the page that asks for a reason.
    """
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent, bg="#0f172a")
        self.controller = controller

        # Centered card
        card = tk.Frame(self, bg="#1e293b", highlightbackground="#334155", highlightthickness=1)
        card.pack(expand=True, fill='both', padx=20, pady=20)

        self.title_label = tk.Label(card, text="🌙 Bedtime - Time for Bed!", font=("Segoe UI", 16, "bold"), bg="#1e293b", fg="#f8fafc")
        self.title_label.pack(pady=(20, 10))

        question = tk.Label(card, text="Why do you need to stay up?", font=("Segoe UI", 11), bg="#1e293b", fg="#94a3b8")
        question.pack(pady=(0, 10))

        self.reason_trials_limiter = tk.Label(card, text=f"Attempts remaining: {controller.no_of_reason_trials}", font=("Segoe UI", 10, "bold"), bg="#1e293b", fg="#ef4444")
        self.reason_trials_limiter.pack(pady=(0, 12))

        self.reason_entry = tk.Entry(card, font=("Segoe UI", 11), width=40, bg="#0f172a", fg="#f8fafc", insertbackground="#f8fafc", relief='solid', bd=1, highlightthickness=1, highlightbackground="#334155")
        self.reason_entry.pack(pady=(0, 20), ipady=4)
        self.reason_entry.focus()

        # Buttons
        btn_row = tk.Frame(card, bg="#1e293b")
        btn_row.pack(pady=10)
        submit_btn = ttk.Button(btn_row, text="✓ Submit Reason", command=controller.check_reason)
        submit_btn.pack(side='left', padx=(0, 10))
        hibernate_btn = ttk.Button(btn_row, text="✕ Hibernate", command=controller.show_final_countdown)
        hibernate_btn.pack(side='left')


class CountdownPage(tk.Frame):
    """
    This is the final countdown page.
    """
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent, bg="#0f172a")
        self.controller = controller
        self.remaining_seconds = 0
        self._after_id = None

        card = tk.Frame(self, bg="#0f172a")
        card.pack(expand=True, fill='both', padx=0, pady=0)

        self.title = tk.Label(
            card,
            text="⚠️ FINAL WARNING",
            font=("Segoe UI", 24, "bold"),
            bg="#0f172a",
            fg="#ef4444"
        )
        self.title.pack(pady=(60, 20))

        # Main countdown display
        self.countdown_label = tk.Label(
            card,
            text="",
            font=("Segoe UI", 20, "bold"),
            bg="#0f172a",
            fg="#f59e0b",
            wraplength=500,
            justify='center'
        )
        self.countdown_label.pack(pady=(0, 40), padx=20)

    def start_countdown(self, countdown_type):
        """Starts or resumes the countdown timer."""
        self.enter_countdown_mode()
        if countdown_type == "hibernate":
            self.remaining_seconds = self.controller.final_countdown
        self.update_countdown_label(countdown_type)

    def update_countdown_label(self, countdown_type):
        """Updates the countdown label recursively."""
        now = datetime.now()
        
        if not self.controller.final_timer_active:
            self.controller.show_frame("StartupPage")
            return
        
        elif now > self.controller.wake_time and now > self.controller.shutdown_time and not self.controller.is_on_break:
            self.controller.show_frame("StartupPage")
            self.controller.grace_timer_active = False
            self.controller.final_timer_active = False
            return
            
        elif self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            if "break" == countdown_type:
                self.countdown_label.config(
                    text=f"Cool down and clear your mind.\nYour break ends in {self.remaining_seconds}s"
                )
            elif "hibernate" == countdown_type:
                self.countdown_label.config(
                    text=f"Shutdown in: {self.remaining_seconds}s"
                )
            self._after_id = self.after(1000, lambda: self.update_countdown_label(countdown_type))
        else:
            if "break" == countdown_type:
                self.exit_countdown_mode()
            elif "hibernate" == countdown_type:
                self.countdown_label.config(text="Hibernating...")
                self.controller.final_timer_active = False
                self.after(1500, lambda: self.controller.hibernate_system())

    def enter_countdown_mode(self):
        """Force countdown UI to occupy the whole screen."""
        self.controller.resizable(False, False)
        self.controller.deiconify()
        self.controller.lift()
        self.controller.focus_force()
        self.controller.attributes("-topmost", True)
        self.controller.state("zoomed")
        self.catch_window_focus_loss()
        
    def catch_window_focus_loss(self):
        """Enforce break mode only when another app truly has foreground focus."""
        if not self.controller.is_on_break:
            return

        try:
            import ctypes
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            GA_ROOT = 2
            focused = user32.GetForegroundWindow()
            if not focused:
                if self.controller.is_on_break:
                    self.after(1000, self.catch_window_focus_loss)
                return

            our_root = user32.GetAncestor(self.controller.winfo_id(), GA_ROOT)
            focused_root = user32.GetAncestor(focused, GA_ROOT)
            same_window = (focused_root == our_root)

            same_process = False
            pid = ctypes.c_ulong(0)
            user32.GetWindowThreadProcessId(focused, ctypes.byref(pid))
            if pid.value == kernel32.GetCurrentProcessId():
                same_process = True

            if not same_window and not same_process:
                self.controller.lift()
                self.controller.focus_force()
                self.controller.attributes("-topmost", True)
                self.controller.state("zoomed")
        except Exception as e:
            print(f"[DEBUG] Focus check error: {e}")

        if self.controller.is_on_break:
            self.after(1000, self.catch_window_focus_loss)

    def exit_countdown_mode(self):
        """Restore normal app window."""
        self.controller.resizable(True, True)
        self.controller.state("normal")
        self.controller.geometry("500x300")
        self.controller.center_window(self.controller, 500, 300)
        self.controller.attributes("-topmost", False)
        self.countdown_label.config(text="Break over. You may continue working.", wraplength=500)
        self.controller.final_timer_active = False
        self.controller.is_on_break = False
        self.after(2000, lambda: self.controller.show_frame("StartupPage"))

    def cancel_countdown(self):
        """Cancel any pending countdown callbacks and reset state."""
        if self._after_id:
            try:
                self.after_cancel(self._after_id)
            except Exception as e:
                print(f"[DEBUG] Error cancelling callback: {e}")
            self._after_id = None
        self.remaining_seconds = 0
        self.controller.final_timer_active = False
        self.controller.is_on_break = False


# --- Main Application (Controller) ---

class SleepEnforcerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # Configure overall style mapping
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Color palette definition (slate dark theme)
        self.bg_dark = "#0f172a"
        self.bg_card = "#1e293b"
        self.text_primary = "#f8fafc"
        
        # Style Combobox
        self.style.configure("TCombobox", 
                             fieldbackground=self.bg_card, 
                             background="#334155", 
                             foreground=self.text_primary, 
                             arrowcolor=self.text_primary,
                             bordercolor="#334155",
                             lightcolor="#334155",
                             darkcolor="#334155")
        
        # Style Buttons
        self.style.configure("TButton", 
                             font=("Segoe UI", 10, "bold"), 
                             background="#3b82f6", 
                             foreground=self.text_primary, 
                             bordercolor="#1d4ed8", 
                             borderwidth=0, 
                             focuscolor="none")
        self.style.map("TButton", 
                       background=[("active", "#2563eb"), ("disabled", "#475569")],
                       foreground=[("disabled", "#94a3b8")])
        
        # Style Checkbuttons
        self.style.configure("TCheckbutton", 
                             background=self.bg_card, 
                             foreground=self.text_primary,
                             font=("Segoe UI", 10))
        self.style.map("TCheckbutton",
                       background=[("active", self.bg_card)],
                       foreground=[("active", self.text_primary)])
        
        # Style Scrollbar
        self.style.configure("Vertical.TScrollbar",
                             background=self.bg_card,
                             troughcolor=self.bg_dark,
                             bordercolor="#334155",
                             arrowcolor="#94a3b8",
                             lightcolor=self.bg_card,
                             darkcolor=self.bg_card)

        # Set main window details
        self.title("Sleep Enforcer")
        self.geometry("500x300")
        self.configure(bg=self.bg_dark)
        
        try:
            icon_path = resource_path("icons\\app_icon.ico") 
            self.iconbitmap(icon_path)
        except Exception as e:
            print(f"Warning: Could not load window icon. {e}")

        self.protocol("WM_DELETE_WINDOW", self.on_minimizing_to_background)
        
        self.current_time = datetime.now()
        self.last_check_time = self.current_time

        # Configuration defaults
        self.warning_time_str = "21:55"
        self.shutdown_time_str = "22:00"
        self.wake_time_str = "06:00"
        self.extension_active = False

        self.grace_period = 180
        self.final_countdown = 60
        self.extension_minutes = 30
        self.grace_timer_active = False
        self.final_timer_active = False
        self.valid_reasons = [
            "deadline", "assignment", "due", "emergency", "meeting"
        ]
        self.no_of_reason_trials = 3
        
        self.strict_break_mode = True
        self.is_on_break = False
        
        self.settings_file_path = self.get_settings_file_path()
        self.load_persistent_settings()
        self.load_assets()
        self.setup_tray()

        # Page frame container
        container = tk.Frame(self, bg=self.bg_dark)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (StartupPage, SettingsPage, ReasonPage, CountdownPage):
            page_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.center_window(self, 500, 300)
        self.show_frame("StartupPage")
        self.check_time()

        self.bind_all('<Return>', self._handle_global_return)
        self.bind('<Unmap>', self.restore_window_on_minimize)

    def _handle_global_return(self, event):
        widget = event.widget
        if isinstance(widget, (ttk.Button, ttk.Checkbutton, tk.Button, tk.Checkbutton)):
            widget.invoke()
            return "break"

    def get_settings_file_path(self):
        app_data_dir = os.getenv("LOCALAPPDATA") or os.path.expanduser("~")
        settings_dir = os.path.join(app_data_dir, "SleepEnforcer")
        os.makedirs(settings_dir, exist_ok=True)
        return os.path.join(settings_dir, "settings.json")

    def save_persistent_settings(self):
        settings_payload = {
            "warning_time": self.warning_time_str,
            "shutdown_time": self.shutdown_time_str,
            "strict_break_mode": self.strict_break_mode,
            "wake_time": self.wake_time_str
        }
        with open(self.settings_file_path, "w", encoding="utf-8") as settings_file:
            json.dump(settings_payload, settings_file, indent=2)

    def load_persistent_settings(self):
        """Loads and resolves rolling sleep schedule configurations."""
        if not os.path.exists(self.settings_file_path):
            self.warning_time, self.shutdown_time, self.wake_time = self.get_active_schedule(self.current_time)
            return

        try:
            with open(self.settings_file_path, "r", encoding="utf-8") as settings_file:
                settings_payload = json.load(settings_file)

            warning_time_str = settings_payload.get("warning_time")
            shutdown_time_str = settings_payload.get("shutdown_time")
            strict_break_mode = settings_payload.get("strict_break_mode")
            wake_time_str = settings_payload.get("wake_time")

            if warning_time_str:
                self.warning_time_str = warning_time_str
            if shutdown_time_str:
                self.shutdown_time_str = shutdown_time_str
            if wake_time_str:
                self.wake_time_str = wake_time_str
            if isinstance(strict_break_mode, bool):
                self.strict_break_mode = strict_break_mode

            self.warning_time, self.shutdown_time, self.wake_time = self.get_active_schedule(datetime.now())
            print(f"[DEBUG] Loaded settings from {self.settings_file_path}")
        except (OSError, ValueError, json.JSONDecodeError) as e:
            print(f"[WARN] Could not load persisted settings: {e}")
            self.warning_time, self.shutdown_time, self.wake_time = self.get_active_schedule(self.current_time)
        
    def get_active_schedule(self, current_time):
        """
        Calculates and returns the active warning_time, shutdown_time, and wake_time datetimes 
        relative to the given current_time, solving midnight transitions and day-rollovers.
        """
        sh, sm = map(int, self.shutdown_time_str.split(':'))
        wh, wm = map(int, self.wake_time_str.split(':'))
        warn_h, warn_m = map(int, self.warning_time_str.split(':'))

        def make_window_for_date(d):
            # Formulate bedtime
            bedtime = datetime.combine(d, datetime_time(hour=sh, minute=sm))
            
            # Formulate wake time
            if (wh, wm) <= (sh, sm):
                # Spans across midnight (ends tomorrow morning)
                wake = datetime.combine(d + timedelta(days=1), datetime_time(hour=wh, minute=wm))
            else:
                # Same day wake time
                wake = datetime.combine(d, datetime_time(hour=wh, minute=wm))
                
            # Formulate warning time
            if (warn_h, warn_m) > (sh, sm):
                # Warning occurs before bedtime (e.g. warning at 23:45, bedtime at 00:15)
                warning = datetime.combine(d - timedelta(days=1), datetime_time(hour=warn_h, minute=warn_m))
            else:
                warning = datetime.combine(d, datetime_time(hour=warn_h, minute=warn_m))
            
            return warning, bedtime, wake


        today_date = current_time.date()
        yesterday_date = today_date - timedelta(days=1)
        tomorrow_date = today_date + timedelta(days=1)

        y_warn, y_bed, y_wake = make_window_for_date(yesterday_date)
        t_warn, t_bed, t_wake = make_window_for_date(today_date)
        tom_warn, tom_bed, tom_wake = make_window_for_date(tomorrow_date)

        # Check if currently inside any active sleep window
        if y_bed <= current_time <= y_wake:
            return y_warn, y_bed, y_wake
        elif t_bed <= current_time <= t_wake:
            return t_warn, t_bed, t_wake
        
        # Daytime: calculate upcoming bedtime
        if current_time < t_bed:
            return t_warn, t_bed, t_wake
        else:
            return tom_warn, tom_bed, tom_wake

    def load_assets(self):
        settings_icon_path = resource_path("icons/settings_icon.png")
        try:
            settings_icon_image = Image.open(settings_icon_path)
            settings_icon_image = settings_icon_image.resize((16, 16), Image.LANCZOS)
            self.settings_icon = ImageTk.PhotoImage(settings_icon_image)
        except Exception as e:
            print(f"Warning: Could not load settings icon. {e}")
            self.settings_icon = ImageTk.PhotoImage(Image.new('RGBA', (16, 16), (0,0,0,0)))

    def show_frame(self, page_name):
        print(f"[DEBUG] Showing frame: {page_name}")
        
        for frame_name, frame in self.frames.items():
            if frame_name != page_name:
                self.disable_all_widgets(frame)
            else:
                self.enable_all_widgets(frame)
        
        frame = self.frames[page_name]
        frame.tkraise()
        frame.focus_set()
        
        self.state('normal')
        self.deiconify()
        self.lift()
        self.focus_force()

    def disable_all_widgets(self, frame):
        for widget in frame.winfo_children():
            try:
                if isinstance(widget, (tk.Entry, ttk.Button, ttk.Combobox, ttk.Checkbutton)):
                    widget.config(state='disabled')
            except tk.TclError:
                pass
            if isinstance(widget, tk.Frame):
                self.disable_all_widgets(widget)

    def enable_all_widgets(self, frame):
        for widget in frame.winfo_children():
            try:
                if isinstance(widget, (tk.Entry, ttk.Button, ttk.Combobox, ttk.Checkbutton)):
                    widget.config(state='normal')
            except tk.TclError:
                pass
            if isinstance(widget, tk.Frame):
                self.enable_all_widgets(widget)

    def save_settings(self):
        self.current_time = datetime.now()
        print("[DEBUG] Saving new settings...")
        
        try:
            settings_page = self.frames["SettingsPage"]
            
            new_warning_time = settings_page.warning_combo.get().strip()
            new_shutdown_time = settings_page.shutdown_combo.get().strip()
            new_wake_time = settings_page.waketime_combo.get().strip()

            def validate_time_str(t_str):
                try:
                    h, m = map(int, t_str.split(':'))
                    if 0 <= h < 24 and 0 <= m < 60:
                        return f"{h:02d}:{m:02d}"
                except Exception:
                    pass
                return None

            v_warning = validate_time_str(new_warning_time)
            v_shutdown = validate_time_str(new_shutdown_time)
            v_wake = validate_time_str(new_wake_time)

            if not v_warning or not v_shutdown or not v_wake:
                messagebox.showerror("Invalid Input", "Please enter times in HH:MM format (e.g. 22:00 or 06:15).", parent=self)
                return

            # Lockout check: sleep changes denied 3 hours close to active bedtime
            lockout_start = self.shutdown_time - timedelta(hours=3)
            if lockout_start <= self.current_time < self.shutdown_time:
                print("[DEBUG] Sleep Time Change Denied")
                messagebox.showerror("Sleep Time Change Denied",
                                      "Sleep Time Changes are not allowed 3 hours close to already set bedtime.", 
                                      parent=self)
                return
            
            self.warning_time_str = v_warning
            self.shutdown_time_str = v_shutdown
            self.wake_time_str = v_wake
            self.strict_break_mode = settings_page.strict_var.get()
            
            # Reset schedule calculations with new strings
            self.warning_time, self.shutdown_time, self.wake_time = self.get_active_schedule(self.current_time)
            self.save_persistent_settings()
            
            self.frames["StartupPage"].update_status()
            messagebox.showinfo("Settings Saved", "Your new times have been saved.", parent=self)
        except Exception as e:
            print(f"[ERROR] Could not save settings: {e}")
            messagebox.showerror("Error", "Could not save settings: Invalid Inputs", parent=self)

    def setup_tray(self):
        try:
            notification_menu = (
                item('Open Sleep Enforcer', self.show_window),
                item('Exit Application', self.exit_app)
            )

            try:
                icon_path = resource_path('icons\\app_icon.ico')
                notification_icon_image = Image.open(icon_path)
            except Exception as e:
                print(f"[ERROR] Tray Icon error {e}")
                notification_icon_image = Image.new('RGB', (64,64), color='red')
            
            self.tray_icon = pystray.Icon("SleepEnforcer", notification_icon_image, f"Sleep Enforcer\nBedtime: {self.shutdown_time_str}", notification_menu)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
            print("[DEBUG] Tray thread started.")
        except Exception as e:
            print(f"[ERROR] Tray initialization failed: {e}")

    def show_window(self, icon=None, item=None):
        self.deiconify() 
        self.state('normal')
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False))
        
    def exit_app(self, icon=None, item=None):
        """Cleanly exits the application, stopping threads and removing the lock file."""
        print("[DEBUG] Exiting application...")
        if hasattr(self, 'tray_icon'):
            self.tray_icon.stop()
        cleanup_lockfile()
        self.destroy()
        sys.exit(0)

    def handle_invalid_reasons(self):
        self.no_of_reason_trials -= 1
        reason_page = self.frames["ReasonPage"]
        reason_page.reason_trials_limiter.config(
            text=f"Attempts remaining: {self.no_of_reason_trials}"
        )
        if self.no_of_reason_trials > 0:
            self.show_custom_warning(
                "Invalid Reason", 
                f"That reason is not accepted.\nYou have {self.no_of_reason_trials} attempts left."
            )
        else:
            self.show_final_countdown()

    def on_minimizing_to_background(self):
        if getattr(self, 'is_on_break', False):
            self.show_custom_warning("Locked", "Hey! Stop trying to evade the break.\nCool down and rest.")
            self.lift()
            self.focus_force()
            return
        
        self.withdraw()
        if hasattr(self, 'tray_icon'):
            try:
                self.tray_icon.notify(
                    "Sleep Enforcer is running in the background. Check Notification Tray.",
                    "Nice try! I'm still here. 👀" 
                )
            except Exception as e:
                print(f"[ERROR] Notification failed: {e}")

    def restore_window_on_minimize(self, event):
        if event.widget == self and self.is_on_break:
            self.deiconify()
            self.lift()
            self.focus_force()

    def center_window(self, window, width, height):
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        window.geometry(f"{width}x{height}+{x}+{y}")

    def check_time(self):
        self.current_time = datetime.now()

        # System resume detection
        delta_seconds = (self.current_time - self.last_check_time).total_seconds()
        self.last_check_time = self.current_time
        
        if delta_seconds > 300:
            print(f"[DEBUG] System resume detected: {delta_seconds}s gap. Handling resume.")
            self.handle_system_resume()
            
        # Reset extension if past wake time
        if getattr(self, 'extension_active', False) and self.current_time > self.wake_time:
            self.extension_active = False
            print("[DEBUG] Extension expired (past wake time). Resetting schedule.")

        # Recalculate schedule if no extension active
        if not getattr(self, 'extension_active', False):
            self.warning_time, self.shutdown_time, self.wake_time = self.get_active_schedule(self.current_time)
            self.warning_time_str = self.warning_time.strftime("%H:%M")
            self.shutdown_time_str = self.shutdown_time.strftime("%H:%M")
            self.wake_time_str = self.wake_time.strftime("%H:%M")
            
            # Sync UI Labels
            try:
                self.frames["StartupPage"].update_status()
            except Exception:
                pass

        if not self.grace_timer_active and not self.final_timer_active:
            # warning time check
            if self.current_time.strftime("%H:%M") == self.warning_time.strftime("%H:%M"):
                print("[DEBUG] WARNING TIME MATCHED! Showing warning...")
                self.show_warning()
            # bedtime check
            elif self.current_time >= self.shutdown_time and self.current_time <= self.wake_time:
                print("[DEBUG] User is awake past the sleep time. Ask the user for a reason")
                self.show_reason_prompt()
            
            self.after(60000, self.check_time)
        else:
            print(f"[DEBUG] Grace/Final timer is still active, check back in 1 minute")
            self.after(60000, self.check_time)

    def handle_system_resume(self):
        """Called when system resumes from hibernation/suspend. Cancels active countdowns."""
        print("[DEBUG] Handling system resume: cancelling active timers.")
        self.grace_timer_active = False
        self.final_timer_active = False
        self.is_on_break = False
        self.extension_active = False

        try:
            cp = self.frames.get("CountdownPage")
            if cp:
                cp.cancel_countdown()
                print("[DEBUG] Countdown cancelled after resume.")
        except Exception as e:
            print(f"[DEBUG] Error cancelling countdown on resume: {e}")

        # Re-resolve schedule instantly
        self.warning_time, self.shutdown_time, self.wake_time = self.get_active_schedule(datetime.now())
        self.warning_time_str = self.warning_time.strftime("%H:%M")
        self.shutdown_time_str = self.shutdown_time.strftime("%H:%M")
        self.wake_time_str = self.wake_time.strftime("%H:%M")

        try:
            self.frames["StartupPage"].update_status()
        except Exception:
            pass
        self.show_frame("StartupPage")

    def show_warning(self):
        self.show_custom_warning(
            "Bedtime Reminder",
            "⏰ 5 minutes until shutdown!\n\nPlease wrap up your work."
        )
    
    def show_custom_warning(self, title, message):
        """Displays a beautiful, non-blocking custom warning window."""
        popup = tk.Toplevel(self)
        popup.title(title)
        popup.configure(bg=self.bg_dark)
        popup.resizable(False, False)
        
        # Configure modal-like behavior but non-blocking
        w, h = 380, 180
        screen_width = popup.winfo_screenwidth()
        screen_height = popup.winfo_screenheight()
        x = (screen_width - w) // 2
        y = (screen_height - h) // 2
        popup.geometry(f"{w}x{h}+{x}+{y}")
        popup.attributes("-topmost", True)
        
        # Style details
        lbl_title = tk.Label(popup, text=title, font=("Segoe UI", 14, "bold"), bg=self.bg_dark, fg="#ef4444")
        lbl_title.pack(pady=(20, 10))
        
        lbl_msg = tk.Label(popup, text=message, font=("Segoe UI", 11), bg=self.bg_dark, fg="#cbd5e1", justify="center", wraplength=340)
        lbl_msg.pack(pady=(0, 20))
        
        btn = ttk.Button(popup, text="OK", command=popup.destroy)
        btn.pack(ipadx=10)
        
        popup.lift()
        popup.focus_force()

    def show_reason_prompt(self):
        self.no_of_reason_trials = 3
        
        # Sync Attempts GUI immediately
        reason_page = self.frames["ReasonPage"]
        reason_page.reason_trials_limiter.config(text=f"Attempts remaining: {self.no_of_reason_trials}")
        reason_page.title_label.config(text=f"🌙 It's {self.shutdown_time_str} - Time for Bed!")
        reason_page.reason_entry.delete(0, 'end')

        self.attributes("-topmost", True)
        self.grace_timer_active = True
        self.show_frame("ReasonPage")
        
        reason_page.reason_entry.focus()
        self.after(self.grace_period * 1000, self.handle_grace_timeout)
        
    def handle_grace_timeout(self):
        if self.grace_timer_active:
            self.grace_timer_active = False
            print("[DEBUG] Grace timer timed out")
            self.show_final_countdown()
    
    def check_reason(self):
        reason_entry = self.frames["ReasonPage"].reason_entry
        reason = reason_entry.get().lower().strip().split()
        
        is_valid = any(valid in reason for valid in self.valid_reasons)
        
        if is_valid:
            self.grace_timer_active = False
            self.extension_active = True
            
            print("[DEBUG] Valid reason provided. Granting extension...")
            self.grant_extension()
            
            # Show a beautiful non-blocking confirmation popup
            self.show_custom_warning(
                "Extension Granted",
                f"✅ Valid reason accepted!\n\nYou have {self.extension_minutes} more minutes."
            )
            
            if self.strict_break_mode:
                self.take_5mins_break()
            else:
                self.frames["StartupPage"].update_status()
                self.show_frame("StartupPage")
        else:
            self.handle_invalid_reasons()
            
        reason_entry.delete(0, 'end')

    def take_5mins_break(self):
        """5-minute break timer (non-blocking layout)"""
        print("[DEBUG] 5 mins break activated")
        countdownpage = self.frames["CountdownPage"]

        self.final_timer_active = True
        self.is_on_break = True

        # Custom calm break themes
        countdownpage.config(bg=self.bg_dark)
        countdownpage.title.config(text="☕ Take a Break", bg=self.bg_dark, fg="#10b981")
        countdownpage.countdown_label.config(bg=self.bg_dark, fg="#34d399")
        
        self.show_frame("CountdownPage")
        
        self.show_custom_warning(
            "5 Minute Break",
            "Please take a 5 minute break before continuing your work."
        )
       
        # Start break countdown instantly in the background!
        countdownpage.remaining_seconds = 300
        countdownpage.start_countdown(countdown_type="break")
     
    def grant_extension(self):
        self.current_time = datetime.now()
        new_shutdown = self.current_time + timedelta(minutes=self.extension_minutes)
        self.shutdown_time = new_shutdown
        self.warning_time = new_shutdown - timedelta(minutes=5)
        self.warning_time_str = self.warning_time.strftime("%H:%M")
        self.shutdown_time_str = self.shutdown_time.strftime("%H:%M")
        print("New times saved after extension")

    def show_final_countdown(self):
        self.attributes("-topmost", True)
        self.final_timer_active = True
        print(f"[DEBUG] Final Countdown Started")
        
        self.show_frame("CountdownPage")
        try:
            countdownpage = self.frames["CountdownPage"]
            countdownpage.config(bg=self.bg_dark)
            countdownpage.countdown_label.config(bg=self.bg_dark, fg="#f59e0b")
            countdownpage.title.config(text="⚠️ FINAL WARNING", bg=self.bg_dark, fg="#ef4444")
            self.frames["CountdownPage"].start_countdown(countdown_type='hibernate')
        except Exception as e:
            print(f"[ERROR] Failed to start countdown: {e}")

    def reopen_reason_prompt(self):
        self.attributes("-topmost", True)
        self.final_timer_active = False
        self.show_frame("ReasonPage")
    
    def hibernate_system(self):
        print("[DEBUG] Hibernating system...")
        self.final_timer_active = False
        self.grace_timer_active = False
        self.show_frame('StartupPage')
        time.sleep(1)
        
        try:
            subprocess.Popen(["cmd", "/c", "timeout /t 2 && shutdown /h && exit"], 
                             creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception as e:
            print(f"Hibernate error: {e}")


if __name__ == "__main__":
    # Create Local App Data directory for logging
    app_data_dir = os.getenv("LOCALAPPDATA") or os.path.expanduser("~")
    log_dir = os.path.join(app_data_dir, "SleepEnforcer")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "sleep_enforcer.log")
    
    # Enable dual logging to console and persistent file
    sys.stdout = DualLogger(log_file, sys.stdout)
    sys.stderr = DualLogger(log_file, sys.stderr)
    
    print(f"\n--- Sleep Enforcer Started at {datetime.now()} ---")
    
    single_instance = SingleInstance()
    app = SleepEnforcerApp()
    app.mainloop()