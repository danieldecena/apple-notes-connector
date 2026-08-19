#!/usr/bin/env python3
"""MCP server exposing Apple Notes via notes.py (osascript-backed).

Lets the Claude desktop app + Claude Code read/write Apple Notes as tools.
Run: .venv/bin/python3 notes_mcp.py  (stdio transport)
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP  # type: ignore[import-not-found]

import notes  # type: ignore[import-not-found]

mcp = FastMCP("apple-notes")


@mcp.tool()
def list_folders() -> list[str]:
    """List all Apple Notes folder names."""
    return notes.list_folders()


@mcp.tool()
def list_notes(folder: str) -> list[dict]:
    """List notes (title + modified) in a folder."""
    return [
        {"title": n.title, "modified": n.modified} for n in notes.list_notes(folder)
    ]


@mcp.tool()
def read_note(title: str, folder: str) -> dict:
    """Read a note's title and body HTML from a folder."""
    n = notes.read_note(title, folder)
    return {"title": n.title, "body": n.body, "folder": folder}


@mcp.tool()
def create_note(
    title: str, body_html: str, folder: str = "Notes", tags: list[str] | None = None
) -> str:
    """Create a note. Body is HTML; title becomes the first line."""
    notes.create_note(title, body_html, folder, tags)
    return f"created '{title}' in {folder}"


@mcp.tool()
def update_note(
    title: str, body_html: str, folder: str = "Notes", tags: list[str] | None = None
) -> str:
    """Replace a note's body. Title is preserved."""
    notes.update_note(title, body_html, folder, tags)
    return f"updated '{title}' in {folder}"


@mcp.tool()
def search_notes(query: str, folder: str | None = None) -> list[dict]:
    """Search notes by text, optionally within one folder."""
    return [
        {"title": n.title, "folder": getattr(n, "folder", folder)}
        for n in notes.search_notes(query, folder)
    ]


if __name__ == "__main__":
    mcp.run()
