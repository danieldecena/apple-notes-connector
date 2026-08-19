#!/usr/bin/env python3
"""
Apple Notes automation library.

Thin, fail-closed wrapper over the Notes.app AppleScript surface. The same
primitives back both the conversational MCP layer and headless sync scripts.

Design notes:
- Note bodies are HTML. Apple Notes derives a note's *title* from the first
  line of its body, so create/update always put the title on line one.
- Body content is handed to osascript via a temp file (AppleScript reads it as
  UTF-8) instead of being interpolated into the script. HTML is full of quotes,
  backslashes, and newlines that would otherwise need fragile shell escaping.
- Folder references honour an optional root folder (NOTES_ROOT_FOLDER) so a
  whole workflow can be scoped to one container without threading it everywhere.
- Every helper raises NotesError on a non-zero osascript exit. Nothing here
  swallows failures — callers decide how to recover.

macOS only. Requires Automation access to Notes.app (granted on first prompt).
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

# Sentinel splitting fields/records in osascript list output. Chosen to be
# vanishingly unlikely to appear inside a note title or body.
_FIELD = "\x1f"  # unit separator
_RECORD = "\x1e"  # record separator


class NotesError(RuntimeError):
    """Raised when an AppleScript call against Notes.app fails."""


@dataclass(frozen=True)
class Note:
    title: str
    body: str  # HTML
    folder: str
    modified: str


def _root_folder() -> str | None:
    root = os.environ.get("NOTES_ROOT_FOLDER", "").strip()
    return root or None


def _esc(value: str) -> str:
    """Escape a string for embedding inside an AppleScript double-quoted literal."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _folder_ref(folder: str) -> str:
    """
    AppleScript expression resolving to the target folder.

    When NOTES_ROOT_FOLDER is set, the folder is looked up as a child of that
    root; otherwise it resolves against the default account's top level.
    """
    root = _root_folder()
    if root:
        return (
            f'(folder "{_esc(folder)}" of (first folder whose name is "{_esc(root)}"))'
        )
    return f'(first folder whose name is "{_esc(folder)}")'


def _run(script: str) -> str:
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if result.returncode != 0:
        raise NotesError(result.stderr.strip() or "osascript failed")
    return result.stdout.rstrip("\n")


def list_folders() -> list[str]:
    """Top-level folder names (excludes Recently Deleted)."""
    raw = _run('tell application "Notes" to get name of every folder')
    return [
        f.strip()
        for f in raw.split(",")
        if f.strip() and f.strip() != "Recently Deleted"
    ]


def ensure_folder(folder: str) -> None:
    """Create the folder if it does not already exist. No-op when present."""
    root = _root_folder()
    if root:
        script = f"""
        tell application "Notes"
            if not (exists (first folder whose name is "{_esc(root)}")) then
                make new folder with properties {{name:"{_esc(root)}"}}
            end if
            set theRoot to first folder whose name is "{_esc(root)}"
            if not (exists (folder "{_esc(folder)}" of theRoot)) then
                make new folder at theRoot with properties {{name:"{_esc(folder)}"}}
            end if
        end tell
        """
    else:
        script = f"""
        tell application "Notes"
            if not (exists (first folder whose name is "{_esc(folder)}")) then
                make new folder with properties {{name:"{_esc(folder)}"}}
            end if
        end tell
        """
    _run(script)


def list_notes(folder: str) -> list[Note]:
    """Every note in a folder, newest-modified order left to AppleScript."""
    script = f"""
    set fieldSep to (ASCII character 31)
    set recSep to (ASCII character 30)
    tell application "Notes"
        set theFolder to {_folder_ref(folder)}
        set out to ""
        repeat with n in (every note in theFolder)
            set out to out & (name of n) & fieldSep & (body of n) & fieldSep & (modification date of n as string) & recSep
        end repeat
        return out
    end tell
    """
    raw = _run(script)
    return _parse_notes(raw, folder)


def _parse_notes(raw: str, folder: str) -> list[Note]:
    notes: list[Note] = []
    for record in raw.split(_RECORD):
        if not record.strip():
            continue
        parts = record.split(_FIELD)
        if len(parts) < 3:
            continue
        notes.append(
            Note(
                title=parts[0].strip(),
                body=parts[1],
                folder=folder,
                modified=parts[2].strip(),
            )
        )
    return notes


def read_note(title: str, folder: str) -> Note:
    """Fetch a single note by exact title within a folder."""
    script = f"""
    set fieldSep to (ASCII character 31)
    tell application "Notes"
        set theFolder to {_folder_ref(folder)}
        set theNote to first note in theFolder whose name is "{_esc(title)}"
        return (body of theNote) & fieldSep & (modification date of theNote as string)
    end tell
    """
    raw = _run(script)
    body, _, modified = raw.partition(_FIELD)
    return Note(title=title, body=body, folder=folder, modified=modified.strip())


def _compose_body(title: str, body_html: str, tags: list[str] | None) -> str:
    """First line becomes the Notes title; tags append as inline #hashtags."""
    hashtags = ""
    if tags:
        hashtags = "<div>" + " ".join(f"#{t.lstrip('#')}" for t in tags) + "</div>"
    return f"<div><b>{title}</b></div>{body_html}{hashtags}"


def _write_body_tempfile(html: str) -> Path:
    fd, path = tempfile.mkstemp(suffix=".html", prefix="applenote_")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(html)
    return Path(path)


def create_note(
    title: str,
    body_html: str = "",
    folder: str = "Notes",
    tags: list[str] | None = None,
) -> None:
    """Create a note. Body is passed via temp file to avoid escaping HTML."""
    ensure_folder(folder)
    full = _compose_body(title, body_html, tags)
    tmp = _write_body_tempfile(full)
    try:
        script = f"""
        tell application "Notes"
            set theBody to (read (POSIX file "{tmp}") as «class utf8»)
            make new note at {_folder_ref(folder)} with properties {{body:theBody}}
        end tell
        """
        _run(script)
    finally:
        tmp.unlink(missing_ok=True)


def update_note(
    title: str,
    body_html: str,
    folder: str = "Notes",
    tags: list[str] | None = None,
) -> None:
    """Replace a note's body wholesale. Title is preserved as the first line."""
    full = _compose_body(title, body_html, tags)
    tmp = _write_body_tempfile(full)
    try:
        script = f"""
        tell application "Notes"
            set theBody to (read (POSIX file "{tmp}") as «class utf8»)
            set theNote to first note in {_folder_ref(folder)} whose name is "{_esc(title)}"
            set body of theNote to theBody
        end tell
        """
        _run(script)
    finally:
        tmp.unlink(missing_ok=True)


def delete_note(title: str, folder: str = "Notes") -> None:
    """Move a note to Recently Deleted."""
    script = f"""
    tell application "Notes"
        delete (first note in {_folder_ref(folder)} whose name is "{_esc(title)}")
    end tell
    """
    _run(script)


def move_note(title: str, from_folder: str, to_folder: str) -> None:
    """Move a note between folders (both resolved under the configured root)."""
    ensure_folder(to_folder)
    script = f"""
    tell application "Notes"
        set theNote to first note in {_folder_ref(from_folder)} whose name is "{_esc(title)}"
        move theNote to {_folder_ref(to_folder)}
    end tell
    """
    _run(script)


def search_notes(query: str, folder: str | None = None) -> list[Note]:
    """Substring match against note titles. Folder-scoped when given."""
    if folder is not None:
        scope = list_notes(folder)
    else:
        scope = [n for f in list_folders() for n in list_notes(f)]
    q = query.lower()
    return [n for n in scope if q in n.title.lower()]
