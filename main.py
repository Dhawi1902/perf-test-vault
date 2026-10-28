"""Launch the vault."""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

import storage
from models import Vault
from ui_window import VaultApp


def _migrate_json_if_needed() -> str:
    """First run after the move to SQLite: bring the old vault.json across.

    The JSON file is renamed rather than deleted, so the original is still
    there if anything about the import looks wrong.
    """
    if storage.DEFAULT_PATH.exists() or not storage.LEGACY_JSON_PATH.exists():
        return ""
    vault = storage.import_json(storage.LEGACY_JSON_PATH, storage.DEFAULT_PATH)
    backup = storage.LEGACY_JSON_PATH.with_suffix(".json.imported")
    storage.LEGACY_JSON_PATH.replace(backup)
    systems = len(vault.systems)
    return (f"Moved {systems} system{'s' if systems != 1 else ''} from vault.json "
            f"into vault.db.\n\nThe original is kept as {backup.name}.")


def _load_or_recover() -> Vault | None:
    """Load the vault. If the file is unusable, offer to set it aside."""
    try:
        note = _migrate_json_if_needed()
        vault = storage.load()
    except storage.StorageError as exc:
        return _recover(exc)
    if note:
        _tell("Vault moved to SQLite", note)
    return vault


def _recover(exc: storage.StorageError) -> Vault | None:
    root = tk.Tk()
    root.withdraw()
    start_fresh = messagebox.askyesno(
        "Vault file problem",
        f"{exc}\n\nMove the file aside and start an empty vault?\n"
        "The original will be kept so you can repair it by hand.",
        icon="error",
    )
    root.destroy()
    if not start_fresh:
        return None
    if storage.DEFAULT_PATH.exists():
        storage.quarantine()
    return Vault()


def _tell(title: str, message: str) -> None:
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo(title, message)
    root.destroy()


def main() -> int:
    vault = _load_or_recover()
    if vault is None:
        return 1
    ctk.set_appearance_mode("system")
    ctk.set_default_color_theme("blue")
    VaultApp(vault, storage.DEFAULT_PATH).mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
