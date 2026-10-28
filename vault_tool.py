"""Look after the vault file without needing any database tool.

    python vault_tool.py init              create an empty vault to start from
    python vault_tool.py info              what is in the vault
    python vault_tool.py export            write it out as readable JSON
    python vault_tool.py export my.json    ... to a file you name
    python vault_tool.py import my.json    replace the vault from a JSON file
    python vault_tool.py backup            copy the vault, date-stamped

Everything here is plain Python and the standard library. `export` then
`import` is also the repair route: read the JSON, fix what is wrong in a text
editor, import it back.
"""

from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

import storage
from models import Vault


def init() -> int:
    """Create an empty vault. Running the app does this too, on first save."""
    if storage.DEFAULT_PATH.exists():
        print(f"Already there: {storage.DEFAULT_PATH}")
        return info()
    storage.save(Vault(), storage.DEFAULT_PATH)
    print(f"Created an empty vault at {storage.DEFAULT_PATH}")
    print("Run `python main.py` and use + System to add your first one.")
    return 0


def info() -> int:
    vault = storage.load()
    if not storage.DEFAULT_PATH.exists():
        print(f"No vault yet at {storage.DEFAULT_PATH}")
        return 0

    size = storage.DEFAULT_PATH.stat().st_size / 1024
    print(f"{storage.DEFAULT_PATH}  ({size:.0f} KB, revision {vault.revision})")
    print(f"{len(vault.systems)} system(s)\n")
    for system in vault.sorted_systems():
        accounts = sum(len(e.accounts) for e in system.environments)
        print(f"  {system.name}  [{system.status}]")
        print(f"    {len(system.folders)} folder(s), {len(system.environments)} environment(s), "
              f"{accounts} account(s)")
        for project in system.projects:
            print(f"    project {project.name!r} ({project.status}): "
                  f"{len(project.plan)} plan item(s), {len(project.log)} log entr(ies)")
    return 0


def export(target: str | None) -> int:
    written = storage.export_json(json_path=Path(target) if target else None)
    print(f"Wrote {written}  ({written.stat().st_size / 1024:.0f} KB)")
    print("Open it in any text editor. `import` puts it back.")
    return 0


def import_from(source: str | None) -> int:
    if not source:
        print("Which file? python vault_tool.py import my.json")
        return 1
    path = Path(source)
    if not path.exists():
        print(f"No such file: {path}")
        return 1

    if storage.DEFAULT_PATH.exists():
        print(f"This REPLACES everything in {storage.DEFAULT_PATH.name}.")
        kept = backup_file()
        print(f"Current vault backed up to {kept.name} first.")
        if input("Type yes to go ahead: ").strip().lower() != "yes":
            print("Nothing changed.")
            return 1

    vault = storage.import_json(path)
    print(f"Imported {len(vault.systems)} system(s) from {path.name}.")
    return 0


def backup_file() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = storage.DEFAULT_PATH.with_name(f"vault-{stamp}.db")
    shutil.copy(storage.DEFAULT_PATH, target)
    return target


def backup() -> int:
    if not storage.DEFAULT_PATH.exists():
        print("Nothing to back up yet.")
        return 1
    target = backup_file()
    print(f"Copied the vault to {target}")
    return 0


def main(argv: list[str]) -> int:
    command = argv[0] if argv else ""
    argument = argv[1] if len(argv) > 1 else None
    try:
        if command == "init":
            return init()
        if command == "info":
            return info()
        if command == "export":
            return export(argument)
        if command == "import":
            return import_from(argument)
        if command == "backup":
            return backup()
    except storage.StorageError as exc:
        print(f"Problem: {exc}")
        return 1
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
