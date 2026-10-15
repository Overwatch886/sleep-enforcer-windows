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
from PIL import Image, ImageTk
import pystray
from pystray import MenuItem as item
from sleep_enforcer import *
import psutil

# Habit coach brain (no Tkinter inside coach/)
from coach.store import Store
from coach.schemas import ActivitySample, EventRecord
from coach.classifier import Classifier
from coach.recommender import Recommender
from coach.explainer import build_explanation
from coach.activity import get_foreground_program_name
from pages.coach_page import CoachPage, CoachSession
from pages.data_page import DataPage
from pages.feedback_page import FeedbackPopup

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

                # --- Habit coach state (design.md) ---
                self.coaching_enabled = True
                self.coach_watch_programs = True
                self.coach_intensity = "normal"
                self._open_coach_session = None
                self.grace_seconds_left = None
                self._feedback_asked_date = None

                self.settings_file_path = self.get_settings_file_path()
                self.load_persistent_settings()

                # Coach brain: store + classifier + recommender.
                # Resilience rule (plan.md NFR): a broken database must never
                # break enforcement — coach is disabled on failure.
                self.store = None
                self.classifier = None
                self.recommender = None
                try:
                    self.store = Store()
                    self.store.open()
                    self.classifier = Classifier(self.store)
                    self.recommender = Recommender(self.store)
                    print("[DEBUG] Coach store opened.")
                except Exception as e:
                    print(f"[WARN] Coach disabled (storage problem): {e}")
                    self.coaching_enabled = False

                self.load_assets()
                self.setup_tray()

                # Page frame container
                container = tk.Frame(self, bg=self.bg_dark)
                container.pack(side="top", fill="both", expand=True)
                container.grid_rowconfigure(0, weight=1)
                container.grid_columnconfigure(0, weight=1)

                self.frames = {}
                for F in (StartupPage, SettingsPage, ReasonPage, CountdownPage,
                          CoachPage, DataPage):
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
                "wake_time": self.wake_time_str,
                "coaching_enabled": self.coaching_enabled,
                "coach_watch_programs": self.coach_watch_programs,
                "coach_intensity": self.coach_intensity
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
                # Coach settings (older settings files simply keep defaults)
                if isinstance(settings_payload.get("coaching_enabled"), bool):
                    self.coaching_enabled = settings_payload["coaching_enabled"]
                if isinstance(settings_payload.get("coach_watch_programs"), bool):
                    self.coach_watch_programs = settings_payload["coach_watch_programs"]
                if settings_payload.get("coach_intensity") in ("gentle", "normal", "firm"):
                    self.coach_intensity = settings_payload["coach_intensity"]
    
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
                # Use after() to let the tray icon settle before sending the notification
                self.after(300, self._send_background_notification)

        def _send_background_notification(self):
            """Sends the background-running notification via the tray icon."""
            try:
                self.tray_icon.notify(
                    "Nice try! I'm still here. 👀",
                    "Sleep Enforcer is running in the background. Check Notification Tray.",
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

                # Morning feedback window: shortly after wake time, offer
                # the one-question next-day popup (once per morning).
                if (self.store is not None
                        and self.current_time > self.wake_time
                        and not getattr(self, "_feedback_asked_date", None)
                                == self.current_time.date()):
                    self._feedback_asked_date = self.current_time.date()
                    self.maybe_ask_feedback()

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
            minutes_until_shutdown = int((self.shutdown_time - self.warning_time).total_seconds() // 60)
            self.show_custom_warning(
                "Bedtime Reminder",
                f"⏰ {minutes_until_shutdown} minutes until shutdown!\n\nPlease wrap up your work."
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

            if self.coaching_enabled and self.store is not None:
                self.start_coach_session()
                return

            # Fallback: the original keyword reason prompt (unchanged)
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
                # Coach: record that the user didn't answer (US: no answer
                # never bypasses enforcement)
                if self._open_coach_session is not None:
                    session = self._open_coach_session
                    self._open_coach_session = None
                    try:
                        self.frames["CoachPage"].stop_timers()
                    except Exception:
                        pass
                    try:
                        self.store.resolve_event(session.event_id, choice="no_answer")
                    except Exception as e:
                        print(f"[DEBUG] no_answer resolve failed: {e}")
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

        # =====================================================
        # Habit coach flow (design.md section 7 — choice handoff)
        # =====================================================

        def start_coach_session(self):
            """Open the bedtime coach screen. Same grace timer rules as the
            old reason prompt: no answer when it expires -> final countdown."""
            print("[DEBUG] Starting coach session")
            self.grace_timer_active = True
            self.grace_seconds_left = self.grace_period

            # 1. What's in front of the user right now (name only, opt-out in settings)
            program_name = ""
            if self.coach_watch_programs:
                program_name = get_foreground_program_name()

            classification = self.classifier.classify(program_name)
            extension_available = not self.store.extension_used_tonight()

            session = CoachSession(
                program_name=program_name,
                classification=classification,
                extension_available=extension_available,
                extension_minutes=self.extension_minutes,
            )

            # 2. Open the event row immediately so the night is recorded
            #    even if the user never answers (choice filled on resolve).
            session.event_id = self.store.save_event(
                EventRecord(
                    started_at=datetime.now(),
                    schedule_bedtime=self.shutdown_time,
                    task=session.task,
                    activity=ActivitySample(
                        program_name=program_name,
                        mapped_category=classification.category,
                    ),
                )
            )

            # 3. Think: score the four options, build the explanation.
            session.recommendation = self.recommender.recommend(
                session.task,
                extension_available=extension_available,
                extension_minutes=self.extension_minutes,
                strict_break_mode=self.strict_break_mode,
            )
            session.recommendation.explanation = build_explanation(
                session.recommendation, session.task, self.extension_minutes)

            self._open_coach_session = session
            self.attributes("-topmost", True)
            self.show_frame("CoachPage")
            self.frames["CoachPage"].start_session(session)

            # 4. Grace countdown — same safety net as before.
            self._countdown_grace()

        def _countdown_grace(self):
            if not self.grace_timer_active or self._open_coach_session is None:
                return
            self.grace_seconds_left -= 1
            if self.grace_seconds_left <= 0:
                self.handle_grace_timeout()
                return
            self.after(1000, self._countdown_grace)

        def coach_fix_guess(self, session, corrected_category, make_rule=False):
            """User corrected the app's guess (US-2: adds, never rewrites)."""
            try:
                self.classifier.learn_correction(
                    session.event_id, session.program_name,
                    session.classification.category, corrected_category,
                    make_rule=make_rule)
                session.task.category = corrected_category
            except Exception as e:
                print(f"[DEBUG] coach_fix_guess failed: {e}")

        def coach_choose(self, session, choice):
            """Hand the user's choice to the existing enforcement machine."""
            print(f"[DEBUG] Coach choice: {choice}")
            self.grace_timer_active = False
            self._open_coach_session = None
            try:
                self.frames["CoachPage"].stop_timers()
            except Exception:
                pass

            followed = (choice == session.recommendation.recommended_choice)

            if choice == "sleep":
                self.store.resolve_event(
                    session.event_id, choice="sleep",
                    recommended_choice=session.recommendation.recommended_choice,
                    recommendation_followed=followed)
                self.show_final_countdown()

            elif choice == "replan":
                replan_title = (session.task.description or
                                session.task.category or "Untitled task")
                self.store.save_replan(
                    session.event_id, replan_title,
                    target_time=datetime.now() + timedelta(hours=12),
                    est_minutes=session.task.est_minutes)
                self.store.resolve_event(
                    session.event_id, choice="replan",
                    recommended_choice=session.recommendation.recommended_choice,
                    recommendation_followed=followed)
                self.show_custom_warning(
                    "Task saved for later",
                    f"📅 '{replan_title}' is saved with a slot tomorrow.\n"
                    f"Time to sleep.")
                self.show_final_countdown()

            elif choice == "continue":
                if not session.extension_available:
                    # Should not happen (button is disabled) — refuse safely.
                    self.show_custom_warning(
                        "Extension used",
                        "Tonight's extension is already used up. Time to sleep.")
                    return
                self.extension_active = True
                self.store.resolve_event(
                    session.event_id, choice="continue", extension_used=True,
                    recommended_choice=session.recommendation.recommended_choice,
                    recommendation_followed=followed)
                self.grant_extension()
                self.show_custom_warning(
                    "Extension Granted",
                    f"✅ You have {self.extension_minutes} more minutes.\n"
                    f"That's the only one tonight — after this, it's sleep.")
                if self.strict_break_mode:
                    self.take_5mins_break()
                else:
                    self.frames["StartupPage"].update_status()
                    self.show_frame("StartupPage")

            elif choice == "break":
                self.store.resolve_event(
                    session.event_id, choice="break",
                    recommended_choice=session.recommendation.recommended_choice,
                    recommendation_followed=followed)
                self.take_5mins_break()

        def maybe_ask_feedback(self):
            """After wake time: offer the one-question next-day popup."""
            if self.store is None:
                return
            try:
                pending = self.store.events_needing_feedback(limit=1)
                if pending:
                    FeedbackPopup(self, pending[0])
            except Exception as e:
                print(f"[DEBUG] Feedback popup failed: {e}")

    
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