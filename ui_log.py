"""The diary for one project: dated prose entries, newest first.

Like the plan, the input box and the filter are kept across redraws so a save
never clears half-written text.
"""

from __future__ import annotations

import customtkinter as ctk

from models import LogEntry, Project, today
from ui_dialogs import Field, ask_form, confirm
from ui_theme import CARD, MUTED, outline_button

_ENTRY_FIELDS = [
    Field("date", "Date", required=True),
    Field("text", "Entry", kind="multiline", required=True),
]


class LogSection(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=CARD, corner_radius=8)
        self._app = app
        self._project: Project | None = None

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=12, pady=(10, 4))
        self._title = ctk.CTkLabel(head, text="LOG", anchor="w", text_color=MUTED,
                                   font=ctk.CTkFont(size=11, weight="bold"))
        self._title.pack(side="left")
        self._filter = ctk.CTkEntry(head, placeholder_text="Filter entries...", width=220,
                                    height=26)
        self._filter.pack(side="right")
        self._filter.bind("<KeyRelease>", lambda _event: self._render_entries())

        self._box = ctk.CTkTextbox(self, height=70)
        self._box.pack(fill="x", padx=12, pady=(4, 6))
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=12, pady=(0, 8))
        self._add_button = ctk.CTkButton(bar, text=f"Add entry for {today()}", width=170,
                                         command=self._add)
        self._add_button.pack(side="left")

        self._entries = ctk.CTkFrame(self, fg_color="transparent")
        self._entries.pack(fill="x", pady=(0, 6))

    def render(self, project: Project | None) -> None:
        self._project = project
        self._render_entries()

    def _render_entries(self) -> None:
        for child in self._entries.winfo_children():
            child.destroy()
        if self._project is None:
            return

        term = self._filter.get().strip().lower()
        shown = [entry for entry in reversed(self._project.log)
                 if not term or term in entry.text.lower() or term in entry.date]
        total = len(self._project.log)
        self._title.configure(
            text=f"LOG  ({len(shown)} of {total})" if term else f"LOG  ({total})")

        if not shown:
            message = "No entry matches that" if term else "Nothing logged yet"
            ctk.CTkLabel(self._entries, text=message, text_color=MUTED, anchor="w").pack(
                fill="x", padx=12, pady=(0, 8))
        for entry in shown:
            self._row(entry)

    def _row(self, entry: LogEntry) -> None:
        row = ctk.CTkFrame(self._entries, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(0, 6))
        row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(row, text=entry.date, width=84, anchor="nw", text_color=MUTED,
                     font=ctk.CTkFont(size=11)).grid(row=0, column=0, sticky="nw", pady=2)
        text = ctk.CTkLabel(row, text=entry.text, anchor="w", justify="left", wraplength=520)
        text.grid(row=0, column=1, sticky="ew")
        text.bind("<Double-Button-1>", lambda _event: self._edit(entry))

        bar = ctk.CTkFrame(row, fg_color="transparent")
        bar.grid(row=0, column=2, sticky="ne")
        outline_button(bar, "Edit", lambda: self._edit(entry), width=44).pack(side="left", padx=2)
        outline_button(bar, "X", lambda: self._delete(entry), width=28,
                       danger=True).pack(side="left", padx=2)

    # --- edits -----------------------------------------------------------

    def _add(self) -> None:
        text = self._box.get("1.0", "end").strip()
        if not text or self._project is None:
            return
        self._project.log.append(LogEntry(date=today(), text=text))
        self._box.delete("1.0", "end")
        self._app.commit()

    def _edit(self, entry: LogEntry) -> None:
        current = {"date": entry.date, "text": entry.text}
        values = ask_form(self.winfo_toplevel(), "Edit entry", _ENTRY_FIELDS, current)
        if values is None or values == current:
            return
        entry.date, entry.text = values["date"], values["text"]
        self._project.log.sort(key=lambda item: item.date)
        self._app.commit()

    def _delete(self, entry: LogEntry) -> None:
        if confirm(self.winfo_toplevel(), "Delete entry", f"Delete the {entry.date} entry?"):
            self._project.log.remove(entry)
            self._app.commit()
