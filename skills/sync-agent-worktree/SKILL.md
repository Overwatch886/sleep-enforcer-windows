---
name: sync-agent-worktree
description: >-
  Synchronize files modified within temporary or sandboxed agent worktrees back to 
  the permanent developer workspace and execute build/test checks there.
metadata:
  version: "1.0"
  author: Antigravity Agent
  workspace: c:\developer\healthy_sleep_enforcer\windows_app
---
# Sync Agent Worktree

## Overview
AI agents are often spawned in dynamic, temporary workspaces (sandboxes under `AppData\Local\.gemini\antigravity\worktrees`). To prevent loss of work and ensure the human user has access to the compiled binaries locally, this skill enforces syncing all modifications back to the permanent developer directory.

## Synced Paths
- **Primary / Permanent Developer Workspace**: `c:\developer\healthy_sleep_enforcer\windows_app`
- **Temporary Sandbox Workspace**: *(Calculated dynamically during execution)*

## Sync & Rebuild Procedure

### Step 1: Copy Source Files
Copy all modified source files, test suites, and configuration files from the temporary worktree back to `c:\developer\healthy_sleep_enforcer\windows_app`.

### Step 2: Rebuild & Validate
Inside the permanent directory (`c:\developer\healthy_sleep_enforcer\windows_app`), perform the following validation:
1. Run `run-headless-tests` to ensure tests pass in the permanent directory.
2. Re-compile the binary via `build-standalone-exe` and `compile-setup-installer` if changes warrant a release.

### Step 3: Workspace Alert Protocol
At the conclusion of the synchronization, the agent must output a message summarizing:
1. The path of the sandboxed workspace where development took place.
2. The path of the permanent workspace where files have been synced.
3. The exact path of the setup installer or executable the user should launch.
