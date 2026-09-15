import tkinter as tk
from tkinter import ttk
from datetime import datetime
import os
import sys
import tempfile
from pystray import MenuItem as item
import psutil
import atexit
class DualLogger:
    """Redirects stdout/stderr to both the terminal console (if available) and a persistent log file."""
    def __init__(self, filepath, terminal_stream):
        self.terminal = terminal_stream
        try:
            self.log = open(filepath, "a", encoding="utf-8")
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
        settings_btn.pack(side='left', padx=5, ipadx=12, ipady=8)
        coach_btn = ttk.Button(actions, text="🧠 Coach & Data", command=lambda: controller.show_frame("DataPage"))
        coach_btn.pack(side='left', padx=5, ipadx=12, ipady=8)

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

