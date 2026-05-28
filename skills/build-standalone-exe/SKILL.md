---
name: build-standalone-exe
description: >-
  Compile a standalone Windows executable (.exe) from the Sleep Enforcer source 
  using PyInstaller in the Conda environment. Includes instructions for bumping 
  the version sequentially beforehand.
metadata:
  version: "1.0"
  author: Antigravity Agent
  workspace: c:\developer\healthy_sleep_enforcer\windows_app
---
# Build Standalone Executable

## Overview
This skill compiles the single-file portable Windows executable `sleep_enforcer-vX.Y.Z.exe` using `pyinstaller` with the configuration defined in `sleep_enforcer.spec`.

## Procedure

### Step 1: Bump Version Number
Before building, update the version string `version = "X.Y.Z"` in `sleep_enforcer.spec` to match the target release version. Also bump the version in `sleep_enforcer_installer.iss` (under `#define AppVersion "X.Y.Z"`).

### Step 2: Compile Standalone Executable
Execute the following PowerShell command in the workspace directory `c:\developer\healthy_sleep_enforcer\windows_app`:

```powershell
conda run -n sleep_enforcer_windows_env pyinstaller sleep_enforcer.spec
```

### Step 3: Verify Output
- Ensure the build finishes without errors.
- The compiled executable will be written to the `dist` directory:
  `dist\sleep_enforcer-vX.Y.Z.exe`
- Proactively verify that the compiled file exists and matches the bumped version.
