"""PLAN & LOG tab: pick a project, then its action plan and its diary."""

from __future__ import annotations

import customtkinter as ctk

from models import STATUSES, Project, System
from ui_dialogs import Field, ask_form, confirm
from ui_log import LogSection
from ui_plan import PlanSection
from ui_theme import MUTED, outline_button

_PROJECT_FIELDS = [
    Field("name", "Project", required=True),
    Field("status", "Status", kind="choice", options=STATUSES),
]


class WorkTab(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._app = app
        self._system: System | None = None
        self._project: Project | None = None

        self._bar = ctk.CTkFrame(self, fg_color="transparent")
        self._bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        self._empty = ctk.CTkLabel(body, text="No project yet. Use + Project to start one.",
                                   text_color=MUTED, anchor="w")
        self._plan = PlanSection(body, app)
        self._log = LogSection(body, app)

    def render(self, system: System | None) -> None:
        self._system = system
        if system is None:
            self._project = None
        elif self._project not in system.projects:
            self._project = _current_project(system)
        self._render_bar()
        self._render_body()

    def show_project(self, project: Project) -> None:
        """Jump straight to one project -- used when opening from the overview."""
        self._project = project
        self._render_bar()
        self._render_body()

    # --- project picker --------------------------------------------------

    def _render_bar(self) -> None:
        for child in self._bar.winfo_children():
            child.destroy()
        if self._system is None:
            return

        names = [_label(p) for p in self._system.projects]
        if names:
            picker = ctk.CTkOptionMenu(self._bar, values=names, width=300,
                                       command=self._pick_project)
            picker.set(_label(self._project) if self._project else names[0])
            picker.pack(side="left")
            outline_button(self._bar, "Edit", self._edit_project, width=56, height=28).pack(
                side="left", padx=6)
            outline_button(self._bar, "Delete", self._delete_project, width=66, height=28,
                           danger=True).pack(side="left")
        ctk.CTkButton(self._bar, text="+ Project", width=96,
                      command=self._add_project).pack(side="right")

    def _pick_project(self, label: str) -> None:
        for project in self._system.projects:
            if _label(project) == label:
                self._project = project
                break
        self._render_body()

    def _render_body(self) -> None:
        for widget in (self._empty, self._plan, self._log):
            widget.pack_forget()
        if self._system is None:
            return
        if self._project is None:
            self._empty.pack(fill="x", padx=6, pady=10)
            return
        self._plan.pack(fill="x", padx=4, pady=(0, 10))
        self._log.pack(fill="x", padx=4, pady=(0, 10))
        self._plan.render(self._project)
        self._log.render(self._project)

    # --- project edits ---------------------------------------------------

    def _add_project(self) -> None:
        values = ask_form(self.winfo_toplevel(), "Add project", _PROJECT_FIELDS)
        if not values:
            return
        project = Project(name=values["name"], status=values["status"])
        self._system.projects.append(project)
        self._project = project
        self._app.commit()

    def _edit_project(self) -> None:
        current = {"name": self._project.name, "status": self._project.status}
        values = ask_form(self.winfo_toplevel(), "Edit project", _PROJECT_FIELDS, current)
        if values and values != current:
            self._project.name = values["name"]
            self._project.status = values["status"]
            self._app.commit()

    def _delete_project(self) -> None:
        if confirm(self.winfo_toplevel(), "Delete project",
                   f"Delete {self._project.name}, its plan and its log?"):
            self._system.projects.remove(self._project)
            self._project = _current_project(self._system)
            self._app.commit()


def _label(project: Project | None) -> str:
    if project is None:
        return ""
    open_items = project.open_items
    suffix = f" - {open_items} open" if open_items else ""
    return f"{project.name}  ({project.status}){suffix}"


def _current_project(system: System) -> Project | None:
    """Prefer the newest active project, then parked, then whatever is last."""
    for status in ("active", "parked"):
        matching = [p for p in system.projects if p.status == status]
        if matching:
            return matching[-1]
    return system.projects[-1] if system.projects else None
