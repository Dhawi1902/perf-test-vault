"""The window: search, the system list, the system header, and the two tabs."""

from __future__ import annotations

from pathlib import Path

import customtkinter as ctk

import storage
from models import System, Vault
from ui_access import AccessTab
from ui_dialogs import Field, ask_form, confirm, warn
from ui_overview import OverviewPane, open_count
from ui_systems import SystemList
from ui_theme import MUTED, outline_button
from ui_work import WorkTab

_STATUS_SECONDS = 4

_SYSTEM_FIELDS = [
    Field("name", "System", required=True),
    Field("app_team", "App team"),
    Field("notes", "Notes", kind="multiline"),
]


class VaultApp(ctk.CTk):
    def __init__(self, vault: Vault, path: Path):
        super().__init__()
        self._vault = vault
        self._path = path
        self._status_job = None
        self._selected: System | None = None
        # Open on the roll-up: the first question of the day is what is waiting.
        self._overview = True

        self.title("Vault")
        self.geometry("1120x700")
        self.minsize(900, 560)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_toolbar()
        self._build_panes()
        self._build_statusbar()
        self.refresh()

    # --- layout ----------------------------------------------------------

    def _build_toolbar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(12, 6))
        bar.grid_columnconfigure(0, weight=1)

        self._search = ctk.CTkEntry(bar, placeholder_text="Search systems, teams, URLs...")
        self._search.grid(row=0, column=0, sticky="ew")
        self._search.bind("<KeyRelease>", lambda _event: self._render_list())
        ctk.CTkButton(bar, text="+ System", width=100,
                      command=self._add_system).grid(row=0, column=1, padx=(8, 0))

    def _build_panes(self) -> None:
        self._list = SystemList(self, self._select, self._show_overview)
        self._list.grid(row=1, column=0, sticky="nsw", padx=(12, 6), pady=(0, 6))

        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=1, column=1, sticky="nsew", padx=(6, 12), pady=(0, 6))
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        self._header = ctk.CTkFrame(right, fg_color="transparent")
        self._header.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self._header.grid_columnconfigure(0, weight=1)

        self._tabs = ctk.CTkTabview(right, anchor="nw")
        self._tabs.grid(row=1, column=0, sticky="nsew")
        self._access = AccessTab(self._tabs.add("ACCESS"), self)
        self._access.pack(fill="both", expand=True)
        self._work = WorkTab(self._tabs.add("PLAN & LOG"), self)
        self._work.pack(fill="both", expand=True)

        self._overview_pane = OverviewPane(right, self, self.open_project)
        self._overview_pane.grid(row=1, column=0, sticky="nsew")

    def _build_statusbar(self) -> None:
        self._statusbar = ctk.CTkLabel(self, text="", anchor="w", text_color=MUTED,
                                       font=ctk.CTkFont(size=11))
        self._statusbar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 8))

    # --- app interface used by the tabs ----------------------------------

    def commit(self) -> None:
        """Save to disk, then redraw. Called after every change."""
        try:
            storage.save(self._vault, self._path)
        except storage.ConflictError as exc:
            warn(self, "Not saved", str(exc))
            return
        except storage.StorageError as exc:
            warn(self, "Could not save", str(exc))
            return
        self.refresh()

    def status(self, message: str) -> None:
        self._statusbar.configure(text=message)
        if self._status_job is not None:
            self.after_cancel(self._status_job)
        self._status_job = self.after(_STATUS_SECONDS * 1000,
                                      lambda: self._statusbar.configure(text=""))

    def refresh(self) -> None:
        if self._selected is not None and self._selected not in self._vault.systems:
            self._selected, self._overview = None, True
        self._render_list()
        self._render_header()
        if self._overview:
            self._tabs.grid_remove()
            self._overview_pane.grid()
            self._overview_pane.render(self._vault)
        else:
            self._overview_pane.grid_remove()
            self._tabs.grid()
            self._access.render(self._selected)
            self._work.render(self._selected)

    # --- rendering -------------------------------------------------------

    def _render_list(self) -> None:
        systems = self._vault.sorted_systems(self._search.get())
        self._list.render(systems, self._selected, self._overview, open_count(self._vault))

    def _render_header(self) -> None:
        for child in self._header.winfo_children():
            child.destroy()
        if self._overview:
            ctk.CTkLabel(self._header, text="All open work", anchor="w",
                         font=ctk.CTkFont(size=20, weight="bold")).grid(
                row=0, column=0, sticky="w", pady=(0, 8))
            return
        system = self._selected
        if system is None:
            ctk.CTkLabel(self._header, text="Select a system on the left", anchor="w",
                         text_color=MUTED).grid(row=0, column=0, sticky="w", pady=8)
            return

        ctk.CTkLabel(self._header, text=system.name, anchor="w",
                     font=ctk.CTkFont(size=20, weight="bold")).grid(
            row=0, column=0, sticky="w")
        subtitle = system.app_team or "no app team set"
        ctk.CTkLabel(self._header, text=subtitle, anchor="w", text_color=MUTED).grid(
            row=1, column=0, sticky="w", pady=(0, 4))

        ctk.CTkLabel(self._header, text=_status_line(system), anchor="e",
                     text_color=MUTED).grid(row=0, column=1, sticky="e", padx=(8, 0))

        bar = ctk.CTkFrame(self._header, fg_color="transparent")
        bar.grid(row=1, column=1, sticky="e", pady=(0, 4))
        outline_button(bar, "Edit", self._edit_system, width=56, height=26).pack(
            side="left", padx=(0, 6))
        outline_button(bar, "Delete", self._delete_system, width=66, height=26,
                       danger=True).pack(side="left")

    # --- actions ---------------------------------------------------------

    def _select(self, system: System | None, refresh_only: bool = False) -> None:
        if not refresh_only:
            self._selected = system
            self._overview = False
        self.refresh()

    def _show_overview(self) -> None:
        self._overview = True
        self.refresh()

    def open_project(self, system: System, project) -> None:
        """Jump from the overview to the project that item belongs to."""
        self._selected, self._overview = system, False
        self.refresh()
        self._tabs.set("PLAN & LOG")
        self._work.show_project(project)

    def _add_system(self) -> None:
        values = ask_form(self, "Add system", _SYSTEM_FIELDS)
        if not values:
            return
        system = System(**values)
        self._vault.systems.append(system)
        self._selected, self._overview = system, False
        self.commit()

    def _edit_system(self) -> None:
        system = self._selected
        current = {field.key: getattr(system, field.key) for field in _SYSTEM_FIELDS}
        values = ask_form(self, "Edit system", _SYSTEM_FIELDS, current)
        if values is None or values == current:
            return
        for key, value in values.items():
            setattr(system, key, value)
        self.commit()

    def _delete_system(self) -> None:
        system = self._selected
        if confirm(self, "Delete system",
                   f"Delete {system.name} with everything in it?\nThis cannot be undone."):
            self._vault.systems.remove(system)
            self._selected, self._overview = None, True
            self.commit()


def _status_line(system: System) -> str:
    """The system's status is read-only -- it comes from its projects."""
    count = len(system.projects)
    if not count:
        return "no projects yet"
    return f"{system.status}  ·  {count} project{'s' if count > 1 else ''}"
