---
name: compile-setup-installer
description: >-
  Compile the Sleep Enforcer Windows Setup Installer (.exe) using Inno Setup compiler 
  (ISCC.exe) based on the 'sleep_enforcer_installer.iss' configuration.
metadata:
  version: "1.0"
  author: Antigravity Agent
  workspace: c:\developer\healthy_sleep_enforcer\windows_app
---
# Compile Setup Installer

## Overview
This skill compiles the professional Windows setup installer `Sleep-Enforcer-vX.Y.Z-Setup.exe` from the Inno Setup script `sleep_enforcer_installer.iss`.

## Prerequisites
- Inno Setup 6 installed on the system (usually at `C:\Program Files (x86)\Inno Setup 6\ISCC.exe`).
- Prior standalone executable compilation completed (the `.iss` script packages the file created by the `build-standalone-exe` skill).

## Procedure

### Step 1: Bump Version Number
Ensure that `#define AppVersion "X.Y.Z"` inside `sleep_enforcer_installer.iss` matches the target version.

### Step 2: Compile Installer
Run the Inno Setup compiler using PowerShell in the workspace directory `c:\developer\healthy_sleep_enforcer\windows_app`:

```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" sleep_enforcer_installer.iss
```

### Step 3: Verify Output
- Ensure Inno Setup completes compilation successfully.
- The setup installer will be placed in the `installer_output` folder:
  `installer_output\Sleep-Enforcer-vX.Y.Z-Setup.exe`
