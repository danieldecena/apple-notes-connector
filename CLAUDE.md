# apple-notes-connector

osascript CRUD over Apple Notes (`notes.py`) plus an MCP stdio server (`notes_mcp.py`). Run: `.venv/bin/python3 notes_mcp.py`.

## Stack
Python 3, FastMCP, AppleScript.

## Do not
- Commit `.venv/`, `*_bak_*`, or `.sync_state*.json`.
- Drive the user's live Notes folders without an explicit ask.
