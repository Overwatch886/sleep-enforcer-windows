from enforcer import SleepEnforcerApp
from sleep_enforcer import  *
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

    # Debug/demo flag: open the coach screen immediately so it can be
    # inspected without waiting for bedtime.
    if "--demo-coach" in sys.argv:
        print("[DEBUG] Demo mode: opening coach session immediately.")
        app.after(1500, app.start_coach_session)

    app.mainloop()