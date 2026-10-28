"""The database shape, kept apart from the code that reads and writes it.

Every child table cascades from its parent, so deleting a system takes its
folders, environments, accounts, projects, plan items and log entries with it
rather than leaving orphans behind. `position` preserves the order things were
put in -- the plan's order is the user's, not the database's.
"""

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS systems (
    id       INTEGER PRIMARY KEY,
    position INTEGER NOT NULL,
    name     TEXT NOT NULL DEFAULT '',
    app_team TEXT NOT NULL DEFAULT '',
    notes    TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS folders (
    id        INTEGER PRIMARY KEY,
    system_id INTEGER NOT NULL REFERENCES systems(id) ON DELETE CASCADE,
    position  INTEGER NOT NULL,
    label     TEXT NOT NULL DEFAULT '',
    path      TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS environments (
    id        INTEGER PRIMARY KEY,
    system_id INTEGER NOT NULL REFERENCES systems(id) ON DELETE CASCADE,
    position  INTEGER NOT NULL,
    name      TEXT NOT NULL DEFAULT '',
    url       TEXT NOT NULL DEFAULT '',
    updated   TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS accounts (
    id             INTEGER PRIMARY KEY,
    environment_id INTEGER NOT NULL REFERENCES environments(id) ON DELETE CASCADE,
    position       INTEGER NOT NULL,
    username       TEXT NOT NULL DEFAULT '',
    password       TEXT NOT NULL DEFAULT '',
    role           TEXT NOT NULL DEFAULT '',
    notes          TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS projects (
    id        INTEGER PRIMARY KEY,
    system_id INTEGER NOT NULL REFERENCES systems(id) ON DELETE CASCADE,
    position  INTEGER NOT NULL,
    name      TEXT NOT NULL DEFAULT '',
    status    TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS plan_items (
    id         INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    position   INTEGER NOT NULL,
    text       TEXT NOT NULL DEFAULT '',
    state      TEXT NOT NULL DEFAULT 'todo',
    done_on    TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS log_entries (
    id         INTEGER PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    position   INTEGER NOT NULL,
    date       TEXT NOT NULL DEFAULT '',
    text       TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_folders_system      ON folders(system_id);
CREATE INDEX IF NOT EXISTS idx_environments_system ON environments(system_id);
CREATE INDEX IF NOT EXISTS idx_accounts_env        ON accounts(environment_id);
CREATE INDEX IF NOT EXISTS idx_projects_system     ON projects(system_id);
CREATE INDEX IF NOT EXISTS idx_plan_project        ON plan_items(project_id);
CREATE INDEX IF NOT EXISTS idx_log_project         ON log_entries(project_id);
"""
