"""Load and save the vault in SQLite.

A save replaces the contents in one transaction: either the whole vault lands
or none of it does. The `revision` counter is checked inside that transaction,
so a second window working from a stale copy is refused rather than allowed to
overwrite the first one's work.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from models import (Account, Environment, Folder, LogEntry, PlanItem, Project,
                    System, Vault)
from schema import SCHEMA

DEFAULT_PATH = Path(__file__).resolve().parent / "data" / "vault.db"
LEGACY_JSON_PATH = DEFAULT_PATH.with_name("vault.json")


class StorageError(Exception):
    """The vault file exists but could not be used."""


class ConflictError(StorageError):
    """Another window saved since this one loaded."""


def load(path: Path | None = None) -> Vault:
    """Read the whole vault. A missing file is normal -- it means first run."""
    path = path or DEFAULT_PATH
    if not path.exists():
        return Vault()
    with closing(_connect(path)) as conn:
        return _read(conn)


def save(vault: Vault, path: Path | None = None) -> None:
    """Replace the stored vault. Raises ConflictError if someone got there first."""
    path = path or DEFAULT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(_connect(path)) as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")
            _check_revision(conn, vault.revision)
            _clear(conn)
            for position, system in enumerate(vault.systems):
                _write_system(conn, position, system)
            conn.execute("INSERT OR REPLACE INTO meta VALUES ('revision', ?)",
                         (str(vault.revision + 1),))
            conn.commit()
        except ConflictError:
            conn.rollback()
            raise
        except sqlite3.Error as exc:
            conn.rollback()
            raise StorageError(f"could not save {path.name}: {exc}") from exc
    vault.revision += 1


def export_json(path: Path | None = None, json_path: Path | None = None) -> Path:
    """Write the whole vault out as readable JSON.

    The escape hatch: the database is not something you can open in a text
    editor, so this turns it back into something you can read and repair.
    """
    path = path or DEFAULT_PATH
    json_path = json_path or path.with_suffix(".export.json")
    vault = load(path)
    payload = json.dumps(vault.to_dict(), indent=2, ensure_ascii=False)
    json_path.write_text(payload, encoding="utf-8")
    return json_path


def import_json(json_path: Path, path: Path | None = None) -> Vault:
    """Load a vault from JSON, replacing whatever the database holds."""
    path = path or DEFAULT_PATH
    try:
        raw = json.loads(json_path.read_text(encoding="utf-8"))
        vault = Vault.from_dict(raw)
    except (json.JSONDecodeError, ValueError, OSError) as exc:
        raise StorageError(f"could not read {json_path.name}: {exc}") from exc
    # Take on the stored revision, otherwise replacing an existing database
    # looks like a stale window trying to overwrite a fresh one.
    if path.exists():
        vault.revision = load(path).revision
    save(vault, path)
    return vault


def quarantine(path: Path | None = None) -> Path:
    """Move an unusable file aside so a fresh vault can be started safely."""
    path = path or DEFAULT_PATH
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    broken = path.with_name(f"{path.stem}.broken-{stamp}{path.suffix}")
    shutil.move(str(path), str(broken))
    return broken


# --- reading ------------------------------------------------------------

def _connect(path: Path) -> sqlite3.Connection:
    try:
        conn = sqlite3.connect(path, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SCHEMA)
        return conn
    except sqlite3.DatabaseError as exc:
        raise StorageError(f"{path.name} is not a usable vault database: {exc}") from exc


def _read(conn: sqlite3.Connection) -> Vault:
    try:
        folders = _by_parent(conn, "folders", "system_id")
        environments = _by_parent(conn, "environments", "system_id")
        accounts = _by_parent(conn, "accounts", "environment_id")
        projects = _by_parent(conn, "projects", "system_id")
        plan_items = _by_parent(conn, "plan_items", "project_id")
        log_entries = _by_parent(conn, "log_entries", "project_id")

        systems = []
        for row in conn.execute("SELECT * FROM systems ORDER BY position"):
            systems.append(System(
                name=row["name"], app_team=row["app_team"], notes=row["notes"],
                folders=[Folder(f["label"], f["path"]) for f in folders.get(row["id"], ())],
                environments=[_environment(e, accounts) for e in environments.get(row["id"], ())],
                projects=[_project(p, plan_items, log_entries)
                          for p in projects.get(row["id"], ())],
            ))
        return Vault(systems=systems, revision=_revision(conn))
    except sqlite3.Error as exc:
        raise StorageError(f"could not read the vault: {exc}") from exc


def _by_parent(conn: sqlite3.Connection, table: str, key: str) -> dict[int, list[sqlite3.Row]]:
    """All rows of one table, grouped by their parent id, in stored order."""
    grouped: dict[int, list[sqlite3.Row]] = {}
    for row in conn.execute(f"SELECT * FROM {table} ORDER BY {key}, position"):
        grouped.setdefault(row[key], []).append(row)
    return grouped


def _environment(row: sqlite3.Row, accounts: dict[int, list[sqlite3.Row]]) -> Environment:
    return Environment(
        name=row["name"], url=row["url"], updated=row["updated"],
        accounts=[Account(a["username"], a["password"], a["role"], a["notes"])
                  for a in accounts.get(row["id"], ())])


def _project(row: sqlite3.Row, plan_items: dict[int, list[sqlite3.Row]],
             log_entries: dict[int, list[sqlite3.Row]]) -> Project:
    return Project(
        name=row["name"], status=row["status"],
        plan=[PlanItem(i["text"], i["state"], i["done_on"]) for i in plan_items.get(row["id"], ())],
        log=[LogEntry(e["date"], e["text"]) for e in log_entries.get(row["id"], ())])


def _revision(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT value FROM meta WHERE key = 'revision'").fetchone()
    return int(row["value"]) if row else 0


# --- writing ------------------------------------------------------------

def _check_revision(conn: sqlite3.Connection, expected: int) -> None:
    stored = _revision(conn)
    if stored != expected:
        raise ConflictError(
            "The vault was changed by another window since this one opened it "
            f"(it is now at revision {stored}, this window has {expected}). "
            "Your change has not been saved. Close the other window, then "
            "reopen this one to pick up its changes.")


def _clear(conn: sqlite3.Connection) -> None:
    """Deleting the systems cascades to everything hanging off them."""
    conn.execute("DELETE FROM systems")


def _write_system(conn: sqlite3.Connection, position: int, system: System) -> None:
    cursor = conn.execute(
        "INSERT INTO systems (position, name, app_team, notes) VALUES (?, ?, ?, ?)",
        (position, system.name, system.app_team, system.notes))
    system_id = cursor.lastrowid

    conn.executemany(
        "INSERT INTO folders (system_id, position, label, path) VALUES (?, ?, ?, ?)",
        [(system_id, i, f.label, f.path) for i, f in enumerate(system.folders)])

    for index, environment in enumerate(system.environments):
        cursor = conn.execute(
            "INSERT INTO environments (system_id, position, name, url, updated) "
            "VALUES (?, ?, ?, ?, ?)",
            (system_id, index, environment.name, environment.url, environment.updated))
        conn.executemany(
            "INSERT INTO accounts (environment_id, position, username, password, role, notes) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [(cursor.lastrowid, i, a.username, a.password, a.role, a.notes)
             for i, a in enumerate(environment.accounts)])

    for index, project in enumerate(system.projects):
        cursor = conn.execute(
            "INSERT INTO projects (system_id, position, name, status) VALUES (?, ?, ?, ?)",
            (system_id, index, project.name, project.status))
        project_id = cursor.lastrowid
        conn.executemany(
            "INSERT INTO plan_items (project_id, position, text, state, done_on) "
            "VALUES (?, ?, ?, ?, ?)",
            [(project_id, i, item.text, item.state, item.done_on)
             for i, item in enumerate(project.plan)])
        conn.executemany(
            "INSERT INTO log_entries (project_id, position, date, text) VALUES (?, ?, ?, ?)",
            [(project_id, i, entry.date, entry.text)
             for i, entry in enumerate(project.log)])
