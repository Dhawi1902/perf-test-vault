"""The action plan for one project.

The input row and the header are built once and kept; only the item rows are
rebuilt on a redraw, so a save elsewhere never swallows what is being typed.
"""

from __future__ import annotations

import customtkinter as ctk

from models import PLAN_STATES, PlanItem, Project, today
from ui_dialogs import Field, ask_form, confirm
from ui_theme import CARD, MUTED, outline_button, state_chip

_NEXT_STATE = dict(zip(PLAN_STATES, PLAN_STATES[1:] + PLAN_STATES[:1]))
_ITEM_FIELDS = [
    Field("text", "Action", required=True),
    Field("state", "State", kind="choice", options=PLAN_STATES),
]


class PlanSection(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=CARD, corner_radius=8)
        self._app = app
        self._project: Project | None = None
        self._show_done = False

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=12, pady=(10, 4))
        self._title = ctk.CTkLabel(head, text="ACTION PLAN", anchor="w", text_color=MUTED,
                                   font=ctk.CTkFont(size=11, weight="bold"))
        self._title.pack(side="left")
        self._done_toggle = ctk.CTkSwitch(head, text="show done", width=40, height=18,
                                          font=ctk.CTkFont(size=11),
                                          command=self._toggle_done)
        self._done_toggle.pack(side="right")

        self._rows = ctk.CTkFrame(self, fg_color="transparent")
        self._rows.pack(fill="x")

        add = ctk.CTkFrame(self, fg_color="transparent")
        add.pack(fill="x", padx=12, pady=(6, 12))
        self._entry = ctk.CTkEntry(add, placeholder_text="Next action...")
        self._entry.pack(side="left", fill="x", expand=True)
        self._entry.bind("<Return>", lambda _event: self._add())
        ctk.CTkButton(add, text="Add", width=60, command=self._add).pack(side="left", padx=(6, 0))

    def render(self, project: Project | None) -> None:
        self._project = project
        for child in self._rows.winfo_children():
            child.destroy()
        if project is None:
            return

        open_count = project.open_items
        waiting = len(project.items_in("waiting"))
        summary = f"ACTION PLAN  ({open_count} open"
        summary += f", {waiting} waiting)" if waiting else ")"
        self._title.configure(text=summary)

        for item in self._ordered(project):
            self._row(item)
        if not project.plan:
            ctk.CTkLabel(self._rows, text="Nothing planned yet", text_color=MUTED,
                         anchor="w").pack(fill="x", padx=12, pady=(0, 4))

    def _ordered(self, project: Project) -> list[PlanItem]:
        """Open items keep the user's order; done ones sink to the bottom."""
        open_items = [item for item in project.plan if not item.done]
        if not self._show_done:
            return open_items
        return open_items + [item for item in project.plan if item.done]

    def _row(self, item: PlanItem) -> None:
        row = ctk.CTkFrame(self._rows, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=1)
        row.grid_columnconfigure(1, weight=1)

        state_chip(row, item.state, lambda: self._advance(item)).grid(row=0, column=0, sticky="w")

        text = ctk.CTkLabel(row, text=item.text, anchor="w", justify="left",
                            text_color=MUTED if item.done else None)
        text.grid(row=0, column=1, sticky="ew", padx=10)
        text.bind("<Double-Button-1>", lambda _event: self._edit(item))

        if item.done and item.done_on:
            ctk.CTkLabel(row, text=item.done_on, text_color=MUTED,
                         font=ctk.CTkFont(size=11)).grid(row=0, column=2, padx=(0, 8))

        bar = ctk.CTkFrame(row, fg_color="transparent")
        bar.grid(row=0, column=3, sticky="e")
        outline_button(bar, "↑", lambda: self._move(item, -1), width=26).pack(side="left", padx=2)
        outline_button(bar, "↓", lambda: self._move(item, 1), width=26).pack(side="left", padx=2)
        outline_button(bar, "Edit", lambda: self._edit(item), width=44).pack(side="left", padx=2)
        outline_button(bar, "X", lambda: self._delete(item), width=28,
                       danger=True).pack(side="left", padx=2)

    # --- edits -----------------------------------------------------------

    def _toggle_done(self) -> None:
        self._show_done = bool(self._done_toggle.get())
        self.render(self._project)

    def _add(self) -> None:
        text = self._entry.get().strip()
        if not text or self._project is None:
            return
        self._project.plan.append(PlanItem(text=text))
        self._entry.delete(0, "end")
        self._app.commit()

    def _advance(self, item: PlanItem) -> None:
        """One click moves an item along: to do -> doing -> waiting -> done."""
        item.state = _NEXT_STATE[item.state]
        item.done_on = today() if item.done else ""
        self._app.status(f"{item.text}: {item.state}")
        self._app.commit()

    def _edit(self, item: PlanItem) -> None:
        current = {"text": item.text, "state": item.state}
        values = ask_form(self.winfo_toplevel(), "Edit action", _ITEM_FIELDS, current)
        if values is None or values == current:
            return
        item.text, item.state = values["text"], values["state"]
        item.done_on = item.done_on or (today() if item.done else "")
        if not item.done:
            item.done_on = ""
        self._app.commit()

    def _move(self, item: PlanItem, offset: int) -> None:
        """Reorder within the open items; done ones are not in the running order."""
        plan = self._project.plan
        order = [i for i in plan if not i.done] if not item.done else [i for i in plan if i.done]
        index = order.index(item)
        target = index + offset
        if not 0 <= target < len(order):
            return
        first, second = plan.index(item), plan.index(order[target])
        plan[first], plan[second] = plan[second], plan[first]
        self._app.commit()

    def _delete(self, item: PlanItem) -> None:
        if confirm(self.winfo_toplevel(), "Delete action", f"Delete \"{item.text}\"?"):
            self._project.plan.remove(item)
            self._app.commit()
