"""Tests for the data layer. Run with: python -m pytest test_vault.py

The UI is checked by using it; these cover what can go wrong quietly:
round-tripping through the database, keeping the order the user chose, not
leaving orphan rows behind, and not letting one window overwrite another.
"""

from __future__ import annotations

import json
import sqlite3

import pytest

import storage
from models import (Account, Environment, Folder, LogEntry, PlanItem, Project,
                    System, Vault)


@pytest.fixture
def db(tmp_path):
    return tmp_path / "vault.db"


@pytest.fixture
def vault() -> Vault:
    return Vault(systems=[
        System(name="Payment Gateway", app_team="Core Banking", notes="phase 2",
               folders=[Folder("Scripts", r"C:\perf\pg"), Folder("Team share", r"C:\od\pg")],
               environments=[Environment(name="SIT", url="https://pg-sit.local",
                                         updated="2026-10-20",
                                         accounts=[Account("perfadmin", "pw", "admin", "n"),
                                                   Account("perfmaker", "pw2", "maker")])],
               projects=[Project(name="Mar 2026",
                                 plan=[PlanItem("smoke run", "done", "2026-10-20"),
                                       PlanItem("ramp", "doing")],
                                 log=[LogEntry("2026-10-20", "kickoff")])]),
        System(name="CRM Portal", projects=[Project(name="2025", status="done")]),
    ])


# --- storage round-trip -------------------------------------------------

def test_roundtrip_preserves_everything(db, vault):
    storage.save(vault, db)
    loaded = storage.load(db)
    assert [s.to_dict() for s in loaded.systems] == [s.to_dict() for s in vault.systems]


def test_missing_file_is_an_empty_vault(tmp_path):
    assert storage.load(tmp_path / "nothing.db").systems == []


def test_save_creates_the_data_folder(tmp_path, vault):
    path = tmp_path / "data" / "vault.db"
    storage.save(vault, path)
    assert path.exists()


def test_saving_twice_does_not_duplicate_rows(db, vault):
    storage.save(vault, db)
    storage.save(vault, db)
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM systems").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == 2


def test_order_is_the_order_the_user_chose(db):
    """Plan order is meaningful -- it must not come back alphabetised."""
    plan = [PlanItem("zebra"), PlanItem("alpha"), PlanItem("middle")]
    project = Project(name="p", plan=plan,
                      log=[LogEntry("2026-01-02", "second"), LogEntry("2026-01-01", "first")])
    storage.save(Vault(systems=[System(name="X", projects=[project])]), db)

    loaded = storage.load(db).systems[0].projects[0]
    assert [i.text for i in loaded.plan] == ["zebra", "alpha", "middle"]
    assert [e.text for e in loaded.log] == ["second", "first"]


def test_many_systems_keep_their_order(db):
    names = [f"System {n}" for n in range(12)]
    storage.save(Vault(systems=[System(name=n) for n in names]), db)
    assert [s.name for s in storage.load(db).systems] == names


def test_deleting_a_system_leaves_no_orphans(db, vault):
    storage.save(vault, db)
    vault.systems.pop(0)
    storage.save(vault, db)

    with sqlite3.connect(db) as conn:
        for table in ("folders", "environments", "accounts", "plan_items", "log_entries"):
            assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0, table
        assert conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 1


# --- concurrency --------------------------------------------------------

def test_revision_advances_on_each_save(db, vault):
    assert vault.revision == 0
    storage.save(vault, db)
    assert vault.revision == 1
    storage.save(vault, db)
    assert vault.revision == 2
    assert storage.load(db).revision == 2


def test_a_stale_window_cannot_overwrite_a_fresh_one(db, vault):
    """Two windows open: the second must not silently clobber the first."""
    storage.save(vault, db)
    first = storage.load(db)
    second = storage.load(db)

    first.systems[0].name = "Renamed by window one"
    storage.save(first, db)

    second.systems[0].name = "Renamed by window two"
    with pytest.raises(storage.ConflictError, match="changed by another window"):
        storage.save(second, db)

    assert storage.load(db).systems[0].name == "Renamed by window one"


def test_a_refused_save_changes_nothing(db, vault):
    storage.save(vault, db)
    stale = storage.load(db)
    storage.save(storage.load(db), db)

    stale.systems.clear()
    with pytest.raises(storage.ConflictError):
        storage.save(stale, db)
    assert len(storage.load(db).systems) == 2


# --- damaged files ------------------------------------------------------

def test_a_file_that_is_not_a_database_is_reported(db):
    db.write_bytes(b"this is not a database at all, not even close")
    with pytest.raises(storage.StorageError, match="not a usable vault database"):
        storage.load(db)


def test_quarantine_moves_the_file_aside(db):
    db.write_bytes(b"rubbish")
    moved = storage.quarantine(db)
    assert moved.exists() and not db.exists()


# --- importing the old JSON vault ---------------------------------------

def test_import_json_brings_everything_across(tmp_path, db):
    source = tmp_path / "vault.json"
    source.write_text(json.dumps({"systems": [{
        "name": "Legacy", "app_team": "Team",
        "folders": [{"label": "Scripts", "path": "C:/perf"}],
        "environments": [{"name": "SIT", "url": "https://x", "accounts": [
            {"username": "u", "password": "p", "role": "admin"}]}],
        "projects": [{"name": "p", "status": "active", "plan": [{"text": "a", "state": "waiting"}],
                      "log": [{"date": "2026-01-01", "text": "note"}]}],
    }]}), encoding="utf-8")

    storage.import_json(source, db)
    system = storage.load(db).systems[0]
    assert system.name == "Legacy"
    assert [(f.label, f.path) for f in system.folders] == [("Scripts", "C:/perf")]
    assert system.environments[0].accounts[0].username == "u"
    assert system.projects[0].plan[0].state == "waiting"
    assert system.projects[0].log[0].text == "note"


def test_import_json_upgrades_the_oldest_shapes(tmp_path, db):
    """A file from before folders were a list and before plan items had states."""
    source = tmp_path / "vault.json"
    source.write_text(json.dumps({"systems": [{
        "name": "Ancient", "status": "done",
        "local_path": "C:/perf", "onedrive_path": "C:/od",
        "projects": [{"name": "p", "status": "active",
                      "plan": [{"text": "ticked", "done": True},
                               {"text": "not ticked", "done": False}]}],
    }]}), encoding="utf-8")

    storage.import_json(source, db)
    system = storage.load(db).systems[0]
    assert [(f.label, f.path) for f in system.folders] == [("Local", "C:/perf"),
                                                           ("OneDrive", "C:/od")]
    assert [i.state for i in system.projects[0].plan] == ["done", "todo"]
    assert system.status == "active", "status is derived from the live project"


def test_import_json_rejects_a_broken_file(tmp_path, db):
    source = tmp_path / "vault.json"
    source.write_text("{ not json", encoding="utf-8")
    with pytest.raises(storage.StorageError, match="could not read"):
        storage.import_json(source, db)


# --- model behaviour ----------------------------------------------------

def test_sorted_systems_puts_active_first_then_alphabetical(vault):
    vault.systems.append(System(name="Aardvark", projects=[Project(status="parked")]))
    vault.systems.append(System(name="Billing", projects=[Project(status="active")]))
    assert [s.name for s in vault.sorted_systems()] == [
        "Billing", "Payment Gateway", "Aardvark", "CRM Portal"]


@pytest.mark.parametrize("term,expected", [
    ("payment", ["Payment Gateway"]),
    ("core banking", ["Payment Gateway"]),
    ("pg-sit", ["Payment Gateway"]),
    ("SIT", ["Payment Gateway"]),
    ("portal", ["CRM Portal"]),
    ("", ["Payment Gateway", "CRM Portal"]),
    ("zzz", []),
])
def test_search(vault, term, expected):
    assert [s.name for s in vault.sorted_systems(term)] == expected


@pytest.mark.parametrize("project_statuses,expected", [
    ([], "active"),
    (["active"], "active"),
    (["done", "active"], "active"),
    (["done", "parked"], "parked"),
    (["done", "done"], "done"),
])
def test_system_status_follows_its_projects(project_statuses, expected):
    system = System(name="X", projects=[Project(status=s) for s in project_statuses])
    assert system.status == expected


def test_only_done_counts_as_closed():
    project = Project(plan=[PlanItem("a", "todo"), PlanItem("b", "doing"),
                            PlanItem("c", "waiting"), PlanItem("d", "done")])
    assert project.open_items == 3
    assert [i.text for i in project.items_in("waiting")] == ["c"]


def test_an_unknown_plan_state_falls_back_to_todo():
    assert PlanItem.from_dict({"text": "x", "state": "banana"}).state == "todo"


def test_export_then_import_is_a_round_trip(tmp_path, db, vault):
    """The escape hatch has to actually work: out to JSON, back in, unchanged."""
    storage.save(vault, db)
    exported = storage.export_json(db, tmp_path / "out.json")
    assert exported.exists()

    text = exported.read_text(encoding="utf-8")
    assert "Payment Gateway" in text, "the export must be readable in an editor"

    storage.import_json(exported, db)
    assert [s.to_dict() for s in storage.load(db).systems] == [s.to_dict() for s in vault.systems]


def test_importing_over_an_existing_vault_is_not_a_conflict(db, vault, tmp_path):
    """Replacing the vault from JSON must not look like a stale second window."""
    storage.save(vault, db)
    storage.save(storage.load(db), db)
    exported = storage.export_json(db, tmp_path / "out.json")
    storage.import_json(exported, db)
    assert len(storage.load(db).systems) == 2


def test_an_edited_export_comes_back_edited(db, vault, tmp_path):
    storage.save(vault, db)
    exported = storage.export_json(db, tmp_path / "out.json")
    exported.write_text(exported.read_text(encoding="utf-8")
                        .replace("Payment Gateway", "Renamed By Hand"), encoding="utf-8")
    storage.import_json(exported, db)
    assert storage.load(db).systems[0].name == "Renamed By Hand"
