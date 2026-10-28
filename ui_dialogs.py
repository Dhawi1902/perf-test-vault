"""Add/edit popups, shared by every tab.

One generic form dialog drives all of them: pass a list of Fields, get back a
dict of values, or None if the user cancelled.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ui_theme import outline_button


@dataclass
class Field:
    key: str
    label: str
    kind: str = "text"  # text | multiline | folder | choice
    options: tuple[str, ...] = ()
    required: bool = False


@dataclass
class _Row:
    spec: Field
    read: callable


class _FormDialog(ctk.CTkToplevel):
    def __init__(self, parent, title: str, fields: list[Field], values: dict):
        super().__init__(parent)
        self.title(title)
        self.result: dict | None = None
        self.resizable(False, False)
        self.grid_columnconfigure(1, weight=1)

        self._rows = [self._build_row(index, spec, values.get(spec.key, ""))
                      for index, spec in enumerate(fields)]
        self._build_buttons(len(fields))

        self.transient(parent)
        self.after(120, self._focus)
        self.bind("<Escape>", lambda _event: self._cancel())
        self.update_idletasks()
        self._centre(parent)
        self.wait_window()

    def _build_row(self, index: int, spec: Field, value: str) -> _Row:
        label = f"{spec.label} *" if spec.required else spec.label
        ctk.CTkLabel(self, text=label, anchor="w").grid(
            row=index, column=0, padx=(16, 8), pady=6, sticky="nw")

        if spec.kind == "multiline":
            box = ctk.CTkTextbox(self, width=420, height=90)
            box.insert("1.0", value)
            box.grid(row=index, column=1, columnspan=2, padx=(0, 16), pady=6, sticky="ew")
            return _Row(spec, lambda: box.get("1.0", "end").strip())

        if spec.kind == "choice":
            menu = ctk.CTkOptionMenu(self, width=420, values=list(spec.options))
            menu.set(value if value in spec.options else spec.options[0])
            menu.grid(row=index, column=1, columnspan=2, padx=(0, 16), pady=6, sticky="ew")
            return _Row(spec, menu.get)

        entry = ctk.CTkEntry(self, width=420)
        entry.insert(0, value)
        if spec.kind == "folder":
            entry.grid(row=index, column=1, pady=6, sticky="ew")
            ctk.CTkButton(self, text="Browse", width=70,
                          command=lambda: self._browse(entry)).grid(
                row=index, column=2, padx=(8, 16), pady=6)
        else:
            entry.grid(row=index, column=1, columnspan=2, padx=(0, 16), pady=6, sticky="ew")
        return _Row(spec, lambda: entry.get().strip())

    def _build_buttons(self, row: int) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=row, column=0, columnspan=3, padx=16, pady=(10, 16), sticky="e")
        outline_button(bar, "Cancel", self._cancel, width=90, height=28).pack(
            side="left", padx=(0, 8))
        ctk.CTkButton(bar, text="Save", width=90, command=self._submit).pack(side="left")

    def _browse(self, entry) -> None:
        chosen = filedialog.askdirectory(parent=self, initialdir=entry.get() or None)
        if chosen:
            entry.delete(0, "end")
            entry.insert(0, chosen.replace("/", "\\"))

    def _focus(self) -> None:
        try:
            self.grab_set()
            self.focus_force()
        except Exception:
            pass  # window already gone

    def _centre(self, parent) -> None:
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    def _submit(self) -> None:
        values = {row.spec.key: row.read() for row in self._rows}
        missing = [row.spec.label for row in self._rows
                   if row.spec.required and not values[row.spec.key]]
        if missing:
            messagebox.showwarning("Missing", f"{missing[0]} is required.", parent=self)
            return
        self.result = values
        self._close()

    def _cancel(self) -> None:
        self.result = None
        self._close()

    def _close(self) -> None:
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()


def ask_form(parent, title: str, fields: list[Field], values: dict | None = None) -> dict | None:
    """Show a modal form. Returns the entered values, or None if cancelled."""
    return _FormDialog(parent, title, fields, values or {}).result


def confirm(parent, title: str, message: str) -> bool:
    return messagebox.askyesno(title, message, parent=parent, icon="warning")


def warn(parent, title: str, message: str) -> None:
    messagebox.showwarning(title, message, parent=parent)
