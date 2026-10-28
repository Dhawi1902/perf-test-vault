"""Everything still open, across every system, on one screen.

Grouped by system and project, ordered doing -> waiting -> to do, so the things
already in flight and the things blocked on someone else come first.
"""

from __future__ import annotations

import customtkinter as ctk

from models import OPEN_STATES, PLAN_STATES, PlanItem, Project, System, Vault, today
from ui_theme import CARD, MUTED, STATE_COLORS, STATE_LABELS, state_chip

_NEXT_STATE = dict(zip(PLAN_STATES, PLAN_STATES[1:] + PLAN_STATES[:1]))


class OverviewPane(ctk.CTkScrollableFrame):
    def __init__(self, master, app, on_open):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self._app = app
        self._on_open = on_open

    def render(self, vault: Vault) -> None:
        for child in self.winfo_children():
            child.destroy()

        work = _open_work(vault)
        self._summary(work)
        if not work:
            ctk.CTkLabel(self, text="Nothing open. Every action is ticked off.",
                         text_color=MUTED, anchor="w").pack(fill="x", padx=16, pady=16)
            return
        for system, project, items in work:
            self._card(system, project, items)

    def _summary(self, work: list[tuple[System, Project, list[PlanItem]]]) -> None:
        counts = {state: 0 for state in OPEN_STATES}
        for _system, _project, items in work:
            for item in items:
                counts[item.state] += 1

        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=4, pady=(0, 10))
        total = sum(counts.values())
        projects = len(work)
        ctk.CTkLabel(bar, text=f"{total} open across {projects} project"
                               f"{'s' if projects != 1 else ''}",
                     anchor="w", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        # packed right-to-left, so reverse to read doing -> waiting -> to do
        for state in reversed(OPEN_STATES):
            if counts[state]:
                ctk.CTkLabel(bar, text=f"{counts[state]} {STATE_LABELS[state]}",
                             text_color=STATE_COLORS[state],
                             font=ctk.CTkFont(size=12, weight="bold")).pack(side="right", padx=8)

    def _card(self, system: System, project: Project, items: list[PlanItem]) -> None:
        card = ctk.CTkFrame(self, fg_color=CARD, corner_radius=8)
        card.pack(fill="x", padx=4, pady=(0, 10))

        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=14, pady=(10, 2))
        name = ctk.CTkLabel(head, text=system.name, anchor="w",
                            font=ctk.CTkFont(size=15, weight="bold"))
        name.pack(side="left")
        ctk.CTkLabel(head, text=f"   {project.name}", anchor="w", text_color=MUTED).pack(
            side="left")
        ctk.CTkButton(head, text="Open", width=56, height=24,
                      command=lambda: self._on_open(system, project)).pack(side="right")

        for item in items:
            self._row(card, system, project, item)
        ctk.CTkLabel(card, text="", height=4).pack()

    def _row(self, card, system: System, project: Project, item: PlanItem) -> None:
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=1)
        row.grid_columnconfigure(1, weight=1)

        state_chip(row, item.state, lambda: self._advance(item)).grid(row=0, column=0, sticky="w")
        text = ctk.CTkLabel(row, text=item.text, anchor="w", justify="left")
        text.grid(row=0, column=1, sticky="ew", padx=10)
        text.bind("<Double-Button-1>", lambda _event: self._on_open(system, project))

    def _advance(self, item: PlanItem) -> None:
        """Advance an item without leaving the overview."""
        item.state = _NEXT_STATE[item.state]
        item.done_on = today() if item.done else ""
        self._app.commit()


def _open_work(vault: Vault) -> list[tuple[System, Project, list[PlanItem]]]:
    """Open items, newest-busiest first, skipping finished projects entirely."""
    work = []
    for system in vault.sorted_systems():
        for project in system.projects:
            if project.status == "done":
                continue
            items = [item for state in OPEN_STATES for item in project.items_in(state)]
            if items:
                work.append((system, project, items))
    return work


def open_count(vault: Vault) -> int:
    return sum(len(items) for _system, _project, items in _open_work(vault))
