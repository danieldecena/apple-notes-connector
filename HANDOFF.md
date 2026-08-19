---
type: reference
created: 2026-06-04
updated: 2026-06-04
status: active
tags: [automation, dev]
related: []
---
# Session Handoff — Apple Notes reorg + Claude setup

_Session: 2026-06-03 · cwd: `/Users/home` · model: Opus 4.8_

## Done this session

1. **Fixed `apps-fs` MCP** — was pointed at dead path `Documents/Claude/Projects/job-hub/apps`;
   repointed to `Obsidian/Projects/apply/apps`. Now ✓ Connected. (`~/.claude.json`, local scope.)
   The other "7 setup issues" are cloud MCPs needing auth (Canva, Supabase, Workable, etc.) — not local.
2. **Silenced spurious zoxide doctor warning** — added `export _ZO_DOCTOR=0` near top of
   `dotfiles/.zshrc` (symlinked from `~/.zshrc`). Config was already correct; warning only fired from
   non-interactive snapshot shells. **Needs a new terminal / `exec zsh` to take effect.**
3. **Built `notes.py`** — Apple Notes automation library (CRUD over osascript, temp-file bodies,
   configurable root, fail-closed). Imports clean; `list_folders()` works. Lives in this dir.
4. **Started Apple Notes reorg Phase 1** — see status below.

## Approved plan

`~/.claude/plans/delegated-swinging-wren.md` — full reorg plan, 5 phases.

**Final taxonomy** (iCloud, flat top-level): `Inbox · Claude · Job App · Finance · Work · Personal · Reference · Ideas` + `Today`/`Checklist` smart folders.
Decisions locked: Job App stays one folder · Trading→Finance · new Ideas folder · delete junk (show list first) · **title-only** classification (ambiguous → stay in Inbox).

## Current Apple Notes state (verified end of session)

```
iCloud:
  Checklist (9, smart)      ← keep
  Job App   (3, sub=4)      ← keep folder; 4 EMPTY subfolders stuck (see blocker)
  Notes     (346)           ← the catch-all, untouched
  Today     (6, smart)      ← keep
On My Mac:
  Notes     (0)             ← account default, leave
```
Job App's 3 notes: `JobScout — Operations` (stays), `Claude Code — Plugins & Skills` + `Claude Code — Quick Reference` (→ move to Claude).
Job App's 4 stuck empty subfolders: `Applied`, `Config`, `Cowork`, `Top 20 Companies`.

## ⚠️ BLOCKER — AppleScript can't delete nested folders

Phase 1 cleared all **top-level** empties (MCP, Plugins, Skills×2, Top 20 Companies, Applied, Cowork,
Claude Config+child, Config+children). But **nested subfolders under Job App will not delete via osascript** —
`delete (folder "X" of folder "Job App" of account "iCloud")` returns success but is a **silent no-op**
(verified: folder still `exists` immediately after). `move (folder …) to account "iCloud"` (promote-then-delete)
**also fails** (`stillInJobApp=true`). This is a known Notes.app AppleScript limitation.

**Resolution options for next session:**
- **(a) Manual** — delete the 4 Job App subfolders in the Notes UI (3 seconds). Simplest.
- **(b) Recreate** — move Job App's 3 notes to Inbox, delete the whole `Job App` top-level folder
  (top-level delete works), recreate `Job App` clean, move the 1 ops note back.
- Encode whichever in the future `apple-notes` skill so it's not rediscovered.

## Remaining phases (not started)

- **P2** — create `Claude/Finance/Work/Personal/Reference/Ideas`; move 2 Claude notes out of Job App;
  rename `Notes`→`Inbox` (`set name of folder "Notes" of account "iCloud" to "Inbox"`).
- **P3** — purge ~20 junk notes (`New Note`, numeric-only, ≤3-char fragments). **Show list before deleting.**
- **P4** — classify 346 by title keyword (rules in plan §Phase 4) via a `reorg.py --dry-run` → `--apply`.
  `reorg.py` is **not yet written**.
- **P5** — (optional) normalize `#hashtag` casing to lowercase-kebab. Invasive (rewrites bodies).

## How to resume

```bash
cd ~/Documents/Obsidian/Resources/Tooling/apple-notes-connector
source .venv/bin/activate   # Python 3.14, html2text installed
python3 -c "import notes; print(notes.list_folders())"
```
- Library: `notes.py` (new) · existing pull-sync: `notes_connector.py`.
- **Robustness TODO in `notes.py`**: add `NOTES_ACCOUNT` env (default `iCloud`) so `_folder_ref`/
  `list_folders` scope to one account — both accounts have a `Notes` folder, so bare-name lookup is ambiguous.
- osascript gotchas learned: don't `repeat` over live `folders` collections while deleting (refs invalidate
  under iCloud sync); reference folders by explicit path per call; delete-and-verify with retries for sync lag.

## Open recommendation

Wrap `notes.py` as an **`apple-notes` skill** (`~/Documents/.claude/skills/apple-notes/`) and/or a thin
**MCP server** (Layer A of the original sync plan) — the natural home for the osascript limitation knowledge
above. Distinct from the Hermes `apple-notes` skill, which uses the `memo` CLI.

## Task tracker (this session)

1. Delete empty folders — **partial** (top-level done; 4 Job App subfolders blocked, see above)
2. Move 2 misfiled Claude notes — pending
3. Triage 346 — pending (needs `reorg.py`)
4. Normalize tag casing — pending (optional)

---
← [[MOC_Tooling]]
