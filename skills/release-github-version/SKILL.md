---
name: release-github-version
description: >-
  Publish a new release to GitHub by tagging the Git repository locally and pushing the 
  tag, then executing the python release automation script to upload assets.
metadata:
  version: "1.0"
  author: Antigravity Agent
  workspace: c:\developer\healthy_sleep_enforcer\windows_app
---
# Release GitHub Version

## Overview
This skill automates publishing a Sleep Enforcer version. It requires a local Git commit, local Git tagging, and running `create_release.py` to push assets (standalone executable and setup installer) directly to GitHub.

## Prerequisites
- The standalone executable and setup installer must be successfully built.
- All code committed to `agent-dev`.
- A valid GITHUB_TOKEN or Git credentials available.

## Procedure

### Step 1: Git Commit and Tagging
In PowerShell inside the workspace directory `c:\developer\healthy_sleep_enforcer\windows_app`:

```powershell
git commit -am "bump: release vX.Y.Z updates"
git push
git tag vX.Y.Z
git push origin vX.Y.Z
```

### Step 2: Run Release Automation Script
Execute the python release automation script to publish the release:

```powershell
python -u "C:\Users\israelolawuyi.OVERWATCH886\.gemini\antigravity-ide\brain\48afa492-d739-4f45-93a3-5ca24b9efe60\scratch\create_release.py"
```

*(Note: The release script automatically cleans up older duplicate releases on re-runs to avoid asset upload failures)*
