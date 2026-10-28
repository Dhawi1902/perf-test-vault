# Personal Vault — Requirements

Single-user desktop app for managing performance-test systems: their URLs,
login credentials, local/OneDrive folders, and a per-project action plan and diary.

## Problem

Performance test requests arrive via a Microsoft Form whose format varies by
app team. Finding a system's URL and test credentials means digging through form
responses; browser bookmarks don't scale; the shared OneDrive holds ~100 project
folders, most belonging to other people, so navigating to the right one is slow.

## Goal

Two clicks from opening the app to being logged into the system under test, and
one click to the right folder. Plus a running record of what to do next and what
has been done, per test project.

## Scope

- Single user, single machine, local only.
- No encryption, no master password, no masked fields. Credentials are shown
  in plain text — this is a convenience store, not a security product.
- Manual data entry. No import from the Microsoft Form (formats vary, and not
  every request belongs to this user).
- Bulk JMeter test data is out of scope — it lives elsewhere.

## Data model

```
System                        the application under test
├─ name                       "Payment Gateway"
├─ app_team                   requesting team / contact
├─ status                     DERIVED from the projects, never stored
├─ notes
├─ folders[]                  as many as wanted, named by the user
│  ├─ label                   "Scripts" | "Team share" | "Results"
│  └─ path                    any folder on this machine
├─ environments[]             stable across projects
│  ├─ name                    SIT | UAT | PROD | free-form
│  ├─ url
│  ├─ updated                 date creds last changed
│  └─ accounts[]              typically 1-5 per environment
│     ├─ username
│     ├─ password
│     ├─ role                 admin | maker | checker | free-form
│     └─ notes
└─ projects[]                 one per test exercise, kept for look-back
   ├─ name                    "Function A - Mar 2026"
   ├─ status                  active | parked | done
   ├─ plan[]                  ordered list the user controls
   │  ├─ text
   │  ├─ state                todo | doing | waiting | done
   │  └─ done_on              stamped when the item reaches done
   └─ log[]                   diary: date + prose, newest first
```

Credentials belong to the environment, not the project: the same login is used
whichever function is being tested. Folders belong to the system, not the
project — successive projects on one system share the same folders.

## Screens

Single window, two panes.

```
┌─ Vault ───────────────────────────────────────────────────────────┐
│ [ search............ ]                            [+ System]      │
├─────────────────┬─────────────────────────────────────────────────┤
│ ACTIVE          │  Payment Gateway        app team: Core Banking  │
│ ● Payment GW  ◀ │  [Open local]  [Open OneDrive]       active ▾   │
│ ● Loan Origin   ├─────────────────────────────────────────────────┤
│ DONE          ▸ │   ACCESS  │  PLAN & LOG                         │
│                 ├─────────────────────────────────────────────────┤
│                 │  SIT   https://pg-sit.bank.local   [Open][Copy] │
│                 │    perfadmin   Pa55w0rd!    [user][pass]  admin │
│                 │    perfuser1   Test123!     [user][pass]  maker │
│                 │  UAT   https://pg-uat.bank.local   [Open][Copy] │
│                 │    perfadmin   Uat2026!     [user][pass]  admin │
└─────────────────┴─────────────────────────────────────────────────┘
```

**Left pane** — systems, active ones listed first, finished ones under a
collapsed group. Search box filters on system name, URL, and app team.

**Header** — system name, app team, status dropdown, and two buttons that open
the local and OneDrive folders in File Explorer. Buttons disable when the path
is unset or missing.

**ACCESS tab** (default) — environments in order, each showing its URL with
Open (launches browser) and Copy buttons, and its accounts beneath, each row
with Copy-username and Copy-password buttons. Add/edit/delete environments and
accounts.

**PLAN & LOG tab** — project selector (current project preselected), then:
- Plan: ordered checklist, add item, tick off, reorder, delete.
- Log: text box to add an entry, stamped with today's date; entries listed
  newest first.

## Behaviours

- Copy buttons put the value on the clipboard. No auto-clear, no masking.
- Open URL launches the default browser.
- Open folder launches File Explorer at the path; a missing path reports why
  in the status bar instead of failing silently.
- Every change saves immediately to disk. No explicit Save button.
- Writes happen in one transaction, so an interrupted save cannot leave the
  vault half-written.
- Projects are never auto-deleted; closing one sets its status to done, which
  moves the system down the list once no project is still open.
- Sections that hold typed input (the plan's add box, the log's entry box and
  filter) are built once and kept, so a save triggered elsewhere never clears
  half-written text.

## Storage

`data/vault.db` beside the app: SQLite, one table per entity, foreign keys with
`ON DELETE CASCADE` so removing a system takes its children with it. Each child
table carries a `position` column, because the order of plan items is the
user's and must survive a round trip.

A save replaces the contents inside a single transaction: the whole vault lands
or none of it does.

**Concurrency.** A `meta.revision` counter is bumped on every save and checked
inside the save transaction. If a second window saved first, this window's save
is refused with an explanation rather than silently overwriting the other's
work. Without this, two open windows each hold the whole vault in memory and
the last to save wins.

**Migration from JSON.** The vault was JSON until this change. On first run, if
`vault.json` exists and `vault.db` does not, the JSON is imported and renamed
to `vault.json.imported` -- renamed, not deleted, so the original survives if
anything about the import looks wrong. `models.Vault.from_dict` still handles
the older JSON shapes (two fixed folder fields, plan items as a bare `done`
flag), so even an early file imports cleanly.

The file is no longer readable in Notepad. `vault_tool.py` covers that with
stdlib Python only -- no database tool required: `info`, `export` (to readable
JSON), `import` (from an edited JSON file), and `backup`. Export/edit/import is
the supported repair route, and `import` takes a backup before replacing
anything.

## Stack

- Python 3.13
- CustomTkinter (GUI) — the only third-party dependency
- stdlib otherwise: json, pathlib, dataclasses, os.startfile, webbrowser
- Clipboard via Tkinter's built-in clipboard, not pyperclip

No CLI. GUI only.

## Code layout

Flat — no packages, no `__init__.py`. The code is hand-copied onto a company
laptop, so each file must be a single standalone paste into the same folder.

```
main.py          launch the app
models.py        System / Environment / Account / Project dataclasses
storage.py       load + transactional save of vault.db, JSON import/export
schema.py        the table definitions
vault_tool.py    command line: info, export, import, backup (not needed to run the app)
actions.py       clipboard, File Explorer, browser
ui_theme.py      shared colours and button styles (light + dark)
ui_window.py     window shell, search box, system header
ui_systems.py    left pane system list
ui_access.py     ACCESS tab
ui_overview.py   all open work across every system
ui_work.py       PLAN & LOG tab: project picker, hosts the two sections below
ui_plan.py       the action plan section
ui_log.py        the diary section
ui_dialogs.py    add/edit popups, shared by the tabs
test_vault.py    tests for the data layer (not needed to run the app)
```

UI modules depend on `models.py` and `storage.py`, never on each other.
No file over ~150 lines.

## Not building

Encryption, master password, masked fields, clipboard auto-clear, multi-user,
sync, Microsoft Form import, bulk test-data storage, due dates, priorities,
task categories, reporting, charts.

## Future (not now)

Richer task tracking (the "own Asana" idea). The project plan/log structure
should not block that, but nothing is being built toward it yet.
