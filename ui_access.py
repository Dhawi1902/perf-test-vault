"""ACCESS tab: the folders, the URLs, and the accounts to log in with."""

from __future__ import annotations

import customtkinter as ctk

import actions
from models import Account, Environment, Folder, System, today
from ui_dialogs import Field, ask_form, confirm
from ui_theme import CARD, MUTED, heading, outline_button

_ENV_FIELDS = [Field("name", "Environment", required=True), Field("url", "URL")]
_ACCOUNT_FIELDS = [
    Field("username", "Username", required=True),
    Field("password", "Password"),
    Field("role", "Role"),
    Field("notes", "Notes"),
]
_FOLDER_FIELDS = [
    Field("label", "Label", required=True),
    Field("path", "Folder", kind="folder", required=True),
]


class AccessTab(ctk.CTkScrollableFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self._app = app

    def render(self, system: System | None) -> None:
        for child in self.winfo_children():
            child.destroy()
        if system is None:
            return
        self._folders_card(system)
        for environment in system.environments:
            self._environment_card(system, environment)
        ctk.CTkButton(self, text="+ Environment", width=140, height=30,
                      command=lambda: self._add_environment(system)).pack(
            anchor="w", padx=4, pady=(6, 12))

    # --- folders ---------------------------------------------------------

    def _folders_card(self, system: System) -> None:
        card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=8)
        card.pack(fill="x", padx=4, pady=(0, 10))
        heading(card, "FOLDERS").pack(fill="x", padx=14, pady=(10, 4))

        if not system.folders:
            ctk.CTkLabel(card, text="No folders yet", text_color=MUTED, anchor="w").pack(
                fill="x", padx=14, pady=(0, 4))
        for folder in system.folders:
            self._folder_row(card, system, folder)

        outline_button(card, "+ Folder", lambda: self._add_folder(system),
                       width=100, height=26).pack(anchor="w", padx=14, pady=(6, 12))

    def _folder_row(self, card, system: System, folder: Folder) -> None:
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=1)
        row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(row, text=folder.label, anchor="w", width=130,
                     font=ctk.CTkFont(size=13, weight="bold")).grid(row=0, column=0, sticky="w")
        missing = not actions.folder_exists(folder.path)
        shown = f"{folder.path}   (not found)" if missing else folder.path
        ctk.CTkLabel(row, text=shown, anchor="w", text_color=MUTED,
                     font=ctk.CTkFont(size=11)).grid(row=0, column=1, sticky="w", padx=8)

        bar = ctk.CTkFrame(row, fg_color="transparent")
        bar.grid(row=0, column=2, sticky="e")
        ctk.CTkButton(bar, text="Open", width=50, height=24,
                      command=lambda: self._open_folder(folder)).pack(side="left", padx=2)
        outline_button(bar, "Edit", lambda: self._edit_folder(folder),
                       width=44).pack(side="left", padx=2)
        outline_button(bar, "X", lambda: self._delete_folder(system, folder),
                       width=28, danger=True).pack(side="left", padx=2)

    # --- environment card ------------------------------------------------

    def _environment_card(self, system: System, environment: Environment) -> None:
        card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=8)
        card.pack(fill="x", padx=4, pady=(0, 10))
        card.grid_columnconfigure(1, weight=1)
        self._card_header(card, system, environment)
        self._card_url(card, environment)

        if not environment.accounts:
            ctk.CTkLabel(card, text="No accounts yet", text_color=MUTED, anchor="w").grid(
                row=2, column=0, columnspan=3, sticky="w", padx=14, pady=(0, 4))
        for index, account in enumerate(environment.accounts):
            self._account_row(card, environment, account, row=3 + index)

        outline_button(card, "+ Account", lambda: self._add_account(environment),
                       width=100, height=26).grid(
            row=3 + len(environment.accounts), column=0, columnspan=3,
            sticky="w", padx=14, pady=(6, 12))

    def _card_header(self, card, system: System, environment: Environment) -> None:
        stamp = f"creds updated {environment.updated}" if environment.updated else ""
        ctk.CTkLabel(card, text=environment.name or "(unnamed)", anchor="w",
                     font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=14, pady=(10, 2))
        ctk.CTkLabel(card, text=stamp, anchor="w", text_color=MUTED,
                     font=ctk.CTkFont(size=11)).grid(row=0, column=1, sticky="w", pady=(10, 2))

        bar = ctk.CTkFrame(card, fg_color="transparent")
        bar.grid(row=0, column=2, sticky="e", padx=10, pady=(8, 0))
        outline_button(bar, "Edit", lambda: self._edit_environment(environment),
                       width=46).pack(side="left", padx=2)
        outline_button(bar, "Delete", lambda: self._delete_environment(system, environment),
                       width=56, danger=True).pack(side="left", padx=2)

    def _card_url(self, card, environment: Environment) -> None:
        shown = environment.url or "no URL set"
        ctk.CTkLabel(card, text=shown, anchor="w",
                     text_color=None if environment.url else MUTED,
                     font=ctk.CTkFont(size=12)).grid(
            row=1, column=0, columnspan=2, sticky="w", padx=14, pady=(0, 6))
        bar = ctk.CTkFrame(card, fg_color="transparent")
        bar.grid(row=1, column=2, sticky="e", padx=10)
        ctk.CTkButton(bar, text="Open", width=50, height=24,
                      command=lambda: self._open_url(environment)).pack(side="left", padx=2)
        outline_button(bar, "Copy", lambda: self._copy(environment.url, "URL"),
                       width=50).pack(side="left", padx=2)

    def _account_row(self, card, environment: Environment, account: Account, row: int) -> None:
        line = ctk.CTkFrame(card, fg_color="transparent")
        line.grid(row=row, column=0, columnspan=3, sticky="ew", padx=14, pady=1)
        line.grid_columnconfigure(2, weight=1)

        mono = ctk.CTkFont(family="Consolas", size=12)
        ctk.CTkLabel(line, text=account.username, anchor="w", width=130, font=mono).grid(
            row=0, column=0, sticky="w")
        ctk.CTkLabel(line, text=account.password or "-", anchor="w", width=130, font=mono).grid(
            row=0, column=1, sticky="w", padx=(8, 0))
        detail = " / ".join(part for part in (account.role, account.notes) if part)
        ctk.CTkLabel(line, text=detail, anchor="w", text_color=MUTED,
                     font=ctk.CTkFont(size=11)).grid(row=0, column=2, sticky="w", padx=8)

        bar = ctk.CTkFrame(line, fg_color="transparent")
        bar.grid(row=0, column=3, sticky="e")
        ctk.CTkButton(bar, text="user", width=44, height=24,
                      command=lambda: self._copy(account.username, "username")).pack(side="left", padx=2)
        ctk.CTkButton(bar, text="pass", width=44, height=24,
                      command=lambda: self._copy(account.password, "password")).pack(side="left", padx=2)
        outline_button(bar, "Edit", lambda: self._edit_account(environment, account),
                       width=44).pack(side="left", padx=2)
        outline_button(bar, "X", lambda: self._delete_account(environment, account),
                       width=28, danger=True).pack(side="left", padx=2)

    # --- actions ---------------------------------------------------------

    def _copy(self, value: str, label: str) -> None:
        if actions.copy(self, value):
            self._app.status(f"Copied {label}")
        else:
            self._app.status(f"Nothing to copy, no {label} set")

    def _open_url(self, environment: Environment) -> None:
        ok, error = actions.open_url(environment.url)
        self._app.status(f"Opened {environment.name}" if ok else f"Could not open URL: {error}")

    def _open_folder(self, folder: Folder) -> None:
        ok, error = actions.open_folder(folder.path)
        self._app.status(f"Opened {folder.label}" if ok else error)

    def _add_folder(self, system: System) -> None:
        values = ask_form(self.winfo_toplevel(), "Add folder", _FOLDER_FIELDS)
        if values:
            system.folders.append(Folder(label=values["label"], path=values["path"]))
            self._app.commit()

    def _edit_folder(self, folder: Folder) -> None:
        current = {"label": folder.label, "path": folder.path}
        values = ask_form(self.winfo_toplevel(), "Edit folder", _FOLDER_FIELDS, current)
        if values and values != current:
            folder.label, folder.path = values["label"], values["path"]
            self._app.commit()

    def _delete_folder(self, system: System, folder: Folder) -> None:
        if confirm(self.winfo_toplevel(), "Remove folder",
                   f"Remove the {folder.label} shortcut?\nThe folder itself is not touched."):
            system.folders.remove(folder)
            self._app.commit()

    def _add_environment(self, system: System) -> None:
        values = ask_form(self.winfo_toplevel(), "Add environment", _ENV_FIELDS)
        if values:
            system.environments.append(Environment(name=values["name"], url=values["url"]))
            self._app.commit()

    def _edit_environment(self, environment: Environment) -> None:
        values = ask_form(self.winfo_toplevel(), "Edit environment", _ENV_FIELDS,
                          {"name": environment.name, "url": environment.url})
        if values:
            environment.name = values["name"]
            environment.url = values["url"]
            self._app.commit()

    def _delete_environment(self, system: System, environment: Environment) -> None:
        count = len(environment.accounts)
        if confirm(self.winfo_toplevel(), "Delete environment",
                   f"Delete {environment.name} and its {count} account(s)?"):
            system.environments.remove(environment)
            self._app.commit()

    def _add_account(self, environment: Environment) -> None:
        values = ask_form(self.winfo_toplevel(), f"Add account to {environment.name}",
                          _ACCOUNT_FIELDS)
        if values:
            environment.accounts.append(Account(**values))
            environment.updated = today()
            self._app.commit()

    def _edit_account(self, environment: Environment, account: Account) -> None:
        current = {"username": account.username, "password": account.password,
                   "role": account.role, "notes": account.notes}
        values = ask_form(self.winfo_toplevel(), "Edit account", _ACCOUNT_FIELDS, current)
        if values is None or values == current:
            return
        account.username = values["username"]
        account.password = values["password"]
        account.role = values["role"]
        account.notes = values["notes"]
        environment.updated = today()
        self._app.commit()

    def _delete_account(self, environment: Environment, account: Account) -> None:
        if confirm(self.winfo_toplevel(), "Delete account", f"Delete {account.username}?"):
            environment.accounts.remove(account)
            environment.updated = today()
            self._app.commit()
