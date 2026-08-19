#!/usr/bin/env python3
"""
Apple Notes → Obsidian sync.
Pulls notes by folder via AppleScript, converts HTML to Markdown,
writes .md files into the target Obsidian folder.
Skips notes that haven't changed since last sync.
"""

import subprocess
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from datetime import datetime

try:
    import html2text
except ImportError:
    print("Missing dependency. Run: .venv/bin/pip install html2text")
    sys.exit(1)

VAULT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT = VAULT_ROOT / "Areas" / "Communication" / "Notes"
STATE_FILE = Path(__file__).parent / ".sync_state.json"

SKIP_FOLDERS = {"Recently Deleted"}


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def get_folders():
    script = 'tell application "Notes" to get name of every folder'
    result = subprocess.run(
        ["osascript", "-e", script], capture_output=True, text=True, check=True
    )
    return [
        f.strip()
        for f in result.stdout.strip().split(",")
        if f.strip() not in SKIP_FOLDERS
    ]


def get_notes_in_folder(folder_name):
    script = f"""
    tell application "Notes"
        set theFolder to first folder whose name is "{folder_name}"
        set theNotes to every note in theFolder
        set output to {{}}
        repeat with n in theNotes
            set end of output to name of n & "|||" & body of n & "|||" & (modification date of n as string)
        end repeat
        return output
    end tell
    """
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if result.returncode != 0 or not result.stdout.strip():
        return []

    notes = []
    for raw in result.stdout.strip().split(", |||"):
        parts = raw.split("|||")
        if len(parts) >= 2:
            title = parts[0].strip().lstrip(", ")
            body = parts[1].strip()
            modified = parts[2].strip() if len(parts) > 2 else ""
            notes.append((title, body, modified))
    return notes


def html_to_markdown(html_body):
    converter = html2text.HTML2Text()
    converter.ignore_links = False
    converter.ignore_images = True
    converter.body_width = 0
    converter.ignore_emphasis = False
    return converter.handle(html_body).strip()


def safe_filename(title):
    name = re.sub(r'[<>:"/\\|?*]', "-", title)
    return name[:100].strip() or "Untitled"


def sync(output_dir: Path, folders: list[str] | None = None, dry_run: bool = False):
    state = load_state()
    all_folders = get_folders()
    target_folders = folders if folders else all_folders

    created = updated = skipped = 0

    for folder in target_folders:
        if folder not in all_folders:
            print(f"Folder not found: {folder}")
            continue

        folder_dir = output_dir / folder
        if not dry_run:
            folder_dir.mkdir(parents=True, exist_ok=True)

        notes = get_notes_in_folder(folder)
        for title, body, modified in notes:
            content_hash = hashlib.md5((title + body).encode()).hexdigest()
            state_key = f"{folder}/{title}"

            if state.get(state_key) == content_hash:
                skipped += 1
                continue

            markdown = html_to_markdown(body)
            frontmatter = f"---\nsource: apple-notes\nfolder: {folder}\nsynced: {datetime.now().strftime('%Y-%m-%d')}\n---\n\n"
            file_content = frontmatter + f"# {title}\n\n{markdown}"
            filename = safe_filename(title) + ".md"
            filepath = folder_dir / filename

            if dry_run:
                action = "UPDATE" if filepath.exists() else "CREATE"
                print(f"[{action}] {folder}/{filename}")
            else:
                existed = filepath.exists()
                filepath.write_text(file_content)
                state[state_key] = content_hash
                if existed:
                    updated += 1
                else:
                    created += 1

    if not dry_run:
        save_state(state)
        print(
            f"Sync complete — {created} created, {updated} updated, {skipped} unchanged"
        )
    else:
        print(f"Dry run — {created + updated} would change, {skipped} unchanged")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync Apple Notes → Obsidian")
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT, help="Target Obsidian folder"
    )
    parser.add_argument(
        "--folders",
        nargs="+",
        help="Only sync specific folders (e.g. --folders Dev Captures)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview without writing files"
    )
    args = parser.parse_args()

    sync(output_dir=args.output, folders=args.folders, dry_run=args.dry_run)
