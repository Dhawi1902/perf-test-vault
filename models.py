"""Data model for the vault.

System > Environment > Account        how to log in
System > Project > PlanItem/LogEntry  what to do next, what was done
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

VERSION = 1

# Status lives on the project. A system's status is derived from its projects,
# which is why there is only one set of names.
STATUSES = ("active", "parked", "done")

# A plan item moves through these. "waiting" is its own state because most
# delays here are somebody else's: creds, test data, an environment refresh.
PLAN_STATES = ("todo", "doing", "waiting", "done")
OPEN_STATES = ("doing", "waiting", "todo")

_STATUS_ORDER = {name: index for index, name in enumerate(STATUSES)}


def today() -> str:
    return date.today().isoformat()


def _text(raw: object) -> str:
    """Anything from disk becomes a clean string, or an empty one."""
    return raw.strip() if isinstance(raw, str) else ""


def _status(raw: object, allowed: tuple[str, ...]) -> str:
    value = _text(raw).lower()
    return value if value in allowed else allowed[0]


def _dicts(raw: object) -> list[dict]:
    return [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []


@dataclass
class Folder:
    """A named folder on this machine: local scratch, a team share, anything."""

    label: str = ""
    path: str = ""

    @classmethod
    def from_dict(cls, raw: dict) -> Folder:
        return cls(label=_text(raw.get("label")), path=_text(raw.get("path")))

    def to_dict(self) -> dict:
        return {"label": self.label, "path": self.path}


@dataclass
class Account:
    username: str = ""
    password: str = ""
    role: str = ""
    notes: str = ""

    @classmethod
    def from_dict(cls, raw: dict) -> Account:
        return cls(
            username=_text(raw.get("username")),
            password=_text(raw.get("password")),
            role=_text(raw.get("role")),
            notes=_text(raw.get("notes")),
        )

    def to_dict(self) -> dict:
        return {"username": self.username, "password": self.password,
                "role": self.role, "notes": self.notes}


@dataclass
class Environment:
    name: str = ""
    url: str = ""
    updated: str = ""
    accounts: list[Account] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: dict) -> Environment:
        return cls(
            name=_text(raw.get("name")),
            url=_text(raw.get("url")),
            updated=_text(raw.get("updated")),
            accounts=[Account.from_dict(a) for a in _dicts(raw.get("accounts"))],
        )

    def to_dict(self) -> dict:
        return {"name": self.name, "url": self.url, "updated": self.updated,
                "accounts": [a.to_dict() for a in self.accounts]}


@dataclass
class PlanItem:
    text: str = ""
    state: str = "todo"
    done_on: str = ""

    @property
    def done(self) -> bool:
        return self.state == "done"

    @classmethod
    def from_dict(cls, raw: dict) -> PlanItem:
        return cls(text=_text(raw.get("text")),
                   state=_plan_state(raw),
                   done_on=_text(raw.get("done_on")))

    def to_dict(self) -> dict:
        return {"text": self.text, "state": self.state, "done_on": self.done_on}


def _plan_state(raw: dict) -> str:
    """Files written before states had a plain done flag."""
    if raw.get("state"):
        return _status(raw.get("state"), PLAN_STATES)
    return "done" if raw.get("done") else "todo"


@dataclass
class LogEntry:
    date: str = ""
    text: str = ""

    @classmethod
    def from_dict(cls, raw: dict) -> LogEntry:
        return cls(date=_text(raw.get("date")) or today(), text=_text(raw.get("text")))

    def to_dict(self) -> dict:
        return {"date": self.date, "text": self.text}


@dataclass
class Project:
    name: str = ""
    status: str = "active"
    plan: list[PlanItem] = field(default_factory=list)
    log: list[LogEntry] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: dict) -> Project:
        return cls(
            name=_text(raw.get("name")),
            status=_status(raw.get("status"), STATUSES),
            plan=[PlanItem.from_dict(p) for p in _dicts(raw.get("plan"))],
            log=[LogEntry.from_dict(entry) for entry in _dicts(raw.get("log"))],
        )

    def to_dict(self) -> dict:
        return {"name": self.name, "status": self.status,
                "plan": [p.to_dict() for p in self.plan],
                "log": [entry.to_dict() for entry in self.log]}

    @property
    def open_items(self) -> int:
        return sum(1 for item in self.plan if not item.done)

    def items_in(self, state: str) -> list[PlanItem]:
        return [item for item in self.plan if item.state == state]


def _legacy_folders(raw: dict) -> list[Folder]:
    """Older files kept exactly two folders in fields of their own."""
    pairs = (("Local", raw.get("local_path")), ("OneDrive", raw.get("onedrive_path")))
    return [Folder(label=label, path=_text(value)) for label, value in pairs if _text(value)]


@dataclass
class System:
    name: str = ""
    app_team: str = ""
    notes: str = ""
    folders: list[Folder] = field(default_factory=list)
    environments: list[Environment] = field(default_factory=list)
    projects: list[Project] = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: dict) -> System:
        return cls(
            name=_text(raw.get("name")),
            app_team=_text(raw.get("app_team")),
            notes=_text(raw.get("notes")),
            folders=[Folder.from_dict(f) for f in _dicts(raw.get("folders"))] or _legacy_folders(raw),
            environments=[Environment.from_dict(e) for e in _dicts(raw.get("environments"))],
            projects=[Project.from_dict(p) for p in _dicts(raw.get("projects"))],
        )

    def to_dict(self) -> dict:
        return {"name": self.name, "app_team": self.app_team, "notes": self.notes,
                "folders": [f.to_dict() for f in self.folders],
                "environments": [e.to_dict() for e in self.environments],
                "projects": [p.to_dict() for p in self.projects]}

    @property
    def status(self) -> str:
        """Follows the projects: a system is as busy as its busiest project.

        A system with no projects yet counts as active, so something you have
        only just added does not start life hidden at the bottom of the list.
        """
        statuses = {project.status for project in self.projects}
        if not statuses or "active" in statuses:
            return "active"
        if "parked" in statuses:
            return "parked"
        return "done"

    @property
    def sort_key(self) -> tuple[int, str]:
        return _STATUS_ORDER.get(self.status, 0), self.name.lower()

    def matches(self, term: str) -> bool:
        """Search hits the name, app team, and any environment name or URL."""
        term = term.strip().lower()
        if not term:
            return True
        haystack = [self.name, self.app_team, self.notes]
        haystack += [e.name for e in self.environments]
        haystack += [e.url for e in self.environments]
        return any(term in value.lower() for value in haystack)


@dataclass
class Vault:
    version: int = VERSION
    systems: list[System] = field(default_factory=list)
    # Bumped on every save. Lets a second window notice it is working from a
    # stale copy instead of silently overwriting the first one's changes.
    revision: int = 0

    @classmethod
    def from_dict(cls, raw: dict) -> Vault:
        if not isinstance(raw, dict):
            raise ValueError("vault file must contain a JSON object")
        return cls(systems=[System.from_dict(s) for s in _dicts(raw.get("systems"))])

    def to_dict(self) -> dict:
        return {"version": VERSION, "systems": [s.to_dict() for s in self.systems]}

    def sorted_systems(self, term: str = "") -> list[System]:
        return sorted((s for s in self.systems if s.matches(term)), key=lambda s: s.sort_key)
