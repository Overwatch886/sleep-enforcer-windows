---
name: run-local-app
description: >-
  Run the local Python Sleep Enforcer Tkinter desktop application within the 
  designated 'sleep_enforcer_windows_env' Conda environment. Use this whenever 
  the user requests to launch, test run, or preview the active app locally.
metadata:
  version: "1.0"
  author: Antigravity Agent
  workspace: c:\developer\healthy_sleep_enforcer\windows_app
---
# Run Local App

## Overview
This skill executes the Tkinter Sleep Enforcer application (`sleep_enforcer.py`) inside the custom Conda environment `sleep_enforcer_windows_env`. Running within the environment ensures that all required packages (such as `pystray`, `psutil`, `pillow`, `pyinstaller`) are correctly loaded.

## Prerequisites
- Windows OS
- Anaconda/Miniconda installed with environment `sleep_enforcer_windows_env`
- Active branch: `agent-dev`

## Execution Steps

To run the application, execute the following PowerShell command in the workspace directory `c:\developer\healthy_sleep_enforcer\windows_app`:

```powershell
conda run -n sleep_enforcer_windows_env python sleep_enforcer.py
```

### Key Guidelines
- **Dual Logging**: The app will log to stdout and `%LOCALAPPDATA%\SleepEnforcer\sleep_enforcer.log` concurrently.
- **Single Instance**: Running this will check for `%TEMP%\sleep_enforcer.lock` to ensure only one instance is active.
