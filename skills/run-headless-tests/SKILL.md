---
name: run-headless-tests
description: >-
  Execute the headless testing suite ('test_sleep_enforcer.py') of the Windows 
  Sleep Enforcer to verify scheduler calculations, bedtime states, and configuration transitions.
metadata:
  version: "1.0"
  author: Antigravity Agent
  workspace: c:\developer\healthy_sleep_enforcer\windows_app
---
# Run Headless Tests

## Overview
This skill executes the headless testing suite (`test_sleep_enforcer.py`) inside the custom Conda environment. This test suite verifies 4 essential scenarios:
1. **Normal Daytime Config**: Safe operating window.
2. **Active Bedtime Config**: Transition into bedtime warning/shutdown checks.
3. **Morning Resume Config**: Exiting bedtime constraints.
4. **Late Night Config**: Bedtime hours starting after midnight.

All 4 test cases must return a `[SUCCESS]` state for the verification to be complete.

## Execution Steps

Execute the following PowerShell command in the workspace directory `c:\developer\healthy_sleep_enforcer\windows_app`:

```powershell
conda run -n sleep_enforcer_windows_env python test_sleep_enforcer.py
```

### Interpretation of Output
- The output should contain:
  ```text
  Test Suite 1: Daytime - [SUCCESS]
  Test Suite 2: Bedtime Active - [SUCCESS]
  Test Suite 3: Morning Resume - [SUCCESS]
  Test Suite 4: Late Night - [SUCCESS]
  ```
- If any test fails, do NOT commit or compile the application. Review `sleep_enforcer.py` scheduler changes and resolve threading/state logical errors.
