import sys
import os
from datetime import datetime, timedelta
import tkinter as tk

# Import our app
from enforcer import SleepEnforcerApp

def run_tests():
    print("[INFO] Starting Sleep Enforcer Headless Unit Tests...")
    
    # Instantiate the app
    app = SleepEnforcerApp()
    app.withdraw() # Hide the GUI window immediately
    
    # Configure test schedule
    app.warning_time_str = "21:55"
    app.shutdown_time_str = "22:00"
    app.wake_time_str = "06:00"
    
    # ----------------------------------------------------
    # TEST 1: Normal Daytime Schedule
    # If it is 11:30 AM today, the active schedule should be:
    # Bedtime: today at 22:00
    # Wake time: tomorrow at 06:00
    # Warning time: today at 21:55
    # ----------------------------------------------------
    ref_daytime = datetime(2026, 5, 28, 11, 30, 0)
    w, s, wk = app.get_active_schedule(ref_daytime)
    
    assert w == datetime(2026, 5, 28, 21, 55), f"Daytime Warning failed: {w}"
    assert s == datetime(2026, 5, 28, 22, 0), f"Daytime Bedtime failed: {s}"
    assert wk == datetime(2026, 5, 29, 6, 0), f"Daytime Wake failed: {wk}"
    print("[SUCCESS] Test 1: Normal Daytime Schedule passed!")

    # ----------------------------------------------------
    # TEST 2: Active Bedtime Window (Inside sleep window)
    # If it is 11:30 PM (23:30) today, we are in the sleep window.
    # Active schedule should be:
    # Bedtime: today at 22:00 (past)
    # Wake time: tomorrow at 06:00 (future)
    # ----------------------------------------------------
    ref_bedtime = datetime(2026, 5, 28, 23, 30, 0)
    w, s, wk = app.get_active_schedule(ref_bedtime)
    
    assert w == datetime(2026, 5, 28, 21, 55), f"Sleep Window Warning failed: {w}"
    assert s == datetime(2026, 5, 28, 22, 0), f"Sleep Window Bedtime failed: {s}"
    assert wk == datetime(2026, 5, 29, 6, 0), f"Sleep Window Wake failed: {wk}"
    print("[SUCCESS] Test 2: Active Bedtime Window passed!")

    # ----------------------------------------------------
    # TEST 3: Morning Resume (Outside Sleep Window)
    # If the user hibernated at 11:45 PM yesterday and resumes at 8:00 AM today.
    # Today is May 29.
    # Active schedule should be:
    # Bedtime: today (May 29) at 22:00
    # Wake time: tomorrow (May 30) at 06:00
    # ----------------------------------------------------
    ref_morning = datetime(2026, 5, 29, 8, 0, 0)
    w, s, wk = app.get_active_schedule(ref_morning)
    
    assert w == datetime(2026, 5, 29, 21, 55), f"Resume Warning failed: {w}"
    assert s == datetime(2026, 5, 29, 22, 0), f"Resume Bedtime failed: {s}"
    assert wk == datetime(2026, 5, 30, 6, 0), f"Resume Wake failed: {wk}"
    print("[SUCCESS] Test 3: Morning Resume (Outside Sleep Window) passed!")

    # ----------------------------------------------------
    # TEST 4: Late Night / After Midnight Bedtime Config
    # Let's say bedtime is 01:00 AM, wake time is 08:00 AM.
    # If it is 10:00 PM (22:00) today (May 28), we are in the evening before bedtime.
    # The active schedule should be:
    # Bedtime: tomorrow (May 29) at 01:00 AM
    # Wake time: tomorrow (May 29) at 08:00 AM
    # Warning time: today (May 28) at 12:55 AM (which is tomorrow May 29 00:55)
    # ----------------------------------------------------
    app.warning_time_str = "00:55"
    app.shutdown_time_str = "01:00"
    app.wake_time_str = "08:00"
    
    ref_evening = datetime(2026, 5, 28, 22, 0, 0)
    w, s, wk = app.get_active_schedule(ref_evening)
    
    assert s == datetime(2026, 5, 29, 1, 0), f"Late Night Bedtime failed: {s}"
    assert wk == datetime(2026, 5, 29, 8, 0), f"Late Night Wake failed: {wk}"
    assert w == datetime(2026, 5, 29, 0, 55), f"Late Night Warning failed: {w}"
    print("[SUCCESS] Test 4: Late Night / After Midnight Bedtime Config passed!")

    print("[INFO] All tests completed successfully!")
    app.destroy()
    sys.exit(0)

if __name__ == "__main__":
    run_tests()
