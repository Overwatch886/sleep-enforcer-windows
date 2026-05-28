---
name: configure-git-agent-identity
description: >-
  Configure Git locally to use the dedicated agent developer identity. Prevents 
  agent commits from getting mixed up with the user's manual commits.
metadata:
  version: "1.0"
  author: Antigravity Agent
  workspace: c:\developer\healthy_sleep_enforcer\windows_app
---
# Configure Git Agent Identity

## Overview
To maintain a clear and easily auditable Git history, all agent commits must be configured locally under the custom agent identity:
- **Username**: `Antigravity Agent`
- **Email**: `agent@healthy-sleep-enforcer.local`

## Execution Steps

Execute the following PowerShell commands in the local workspace directory `c:\developer\healthy_sleep_enforcer\windows_app`:

```powershell
git config --local user.name "Antigravity Agent"
git config --local user.email "agent@healthy-sleep-enforcer.local"
```

### Verification
To verify that the configuration has been successfully applied, run:

```powershell
git config user.name
git config user.email
```
Ensure they return `Antigravity Agent` and `agent@healthy-sleep-enforcer.local` respectively.
