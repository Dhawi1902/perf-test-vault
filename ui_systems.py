"""Left pane: all open work on top, then the systems, finished ones tucked away."""

from __future__ import annotations

import customtkinter as ctk

from models import System
from ui_theme import MUTED

_SELECTED = ("gray85", "gray25")


class SystemList(ctk.CTkScrollableFrame):
    def __init__(self, master, on_select, on_overview):
        super().__init__(master, width=220, label_text="")
        self.grid_columnconfigure(0, weight=1)
        self._on_select = on_select
        self._on_overview = on_overview
        self._show_done = False

    def render(self, systems: list[System], selected: System | None,
               overview_active: bool, open_count: int) -> None:
        for child in self.winfo_children():
            child.destroy()

        self._overview_row(overview_active, open_count)

        current = [s for s in systems if s.status != "done"]
        finished = [s for s in systems if s.status == "done"]
        if not systems:
            self._placeholder("No systems yet.\nUse + System to add one.")
            return

        last_status = None
        for system in current:
            if system.status != last_status:
                self._heading(system.status.upper())
                last_status = system.status
            self._row(system, selected)

        if finished:
            self._done_toggle(len(finished))
            if self._show_done:
                for system in finished:
                    self._row(system, selected)

    def _overview_row(self, active: bool, open_count: int) -> None:
        label = f"All open work  ({open_count})" if open_count else "All open work"
        ctk.CTkButton(self, text=label, anchor="w", height=34,
                      fg_color=_SELECTED if active else "transparent",
                      text_color=("gray10", "gray95"), hover_color=_SELECTED,
                      font=ctk.CTkFont(size=13, weight="bold" if active else "normal"),
                      command=self._on_overview).pack(fill="x", padx=6, pady=(4, 2))

    def _placeholder(self, text: str) -> None:
        ctk.CTkLabel(self, text=text, text_color=MUTED, justify="left",
                     anchor="w").pack(fill="x", padx=10, pady=12)

    def _heading(self, text: str) -> None:
        ctk.CTkLabel(self, text=text, anchor="w", text_color=MUTED,
                     font=ctk.CTkFont(size=11, weight="bold")).pack(
            fill="x", padx=10, pady=(12, 2))

    def _done_toggle(self, count: int) -> None:
        arrow = "▾" if self._show_done else "▸"
        ctk.CTkButton(self, text=f"{arrow}  DONE ({count})", anchor="w", height=26,
                      fg_color="transparent", text_color=MUTED, hover=False,
                      font=ctk.CTkFont(size=11, weight="bold"),
                      command=self._toggle_done).pack(fill="x", padx=6, pady=(12, 2))

    def _row(self, system: System, selected: System | None) -> None:
        is_selected = selected is not None and system is selected
        open_items = sum(p.open_items for p in system.projects if p.status != "done")
        subtitle = system.app_team or f"{len(system.environments)} environment(s)"
        if open_items:
            subtitle = f"{subtitle}  ·  {open_items} open"

        row = ctk.CTkFrame(self, fg_color=_SELECTED if is_selected else "transparent",
                           corner_radius=6)
        row.pack(fill="x", padx=6, pady=1)
        row.grid_columnconfigure(0, weight=1)

        name = ctk.CTkLabel(row, text=system.name or "(unnamed)", anchor="w",
                            font=ctk.CTkFont(size=13, weight="bold" if is_selected else "normal"))
        name.grid(row=0, column=0, sticky="ew", padx=10, pady=(6, 0))
        team = ctk.CTkLabel(row, text=subtitle, anchor="w", text_color=MUTED,
                            font=ctk.CTkFont(size=11))
        team.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 6))

        for widget in (row, name, team):
            widget.bind("<Button-1>", lambda _event, s=system: self._on_select(s))

    def _toggle_done(self) -> None:
        self._show_done = not self._show_done
        self._on_select(None, refresh_only=True)
