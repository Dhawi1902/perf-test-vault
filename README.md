# Vault

A personal store for the systems I performance-test: their URLs, the test
accounts for each environment, the folders the work lives in, and what is left
to do on each project.

## Run it

```
pip install customtkinter
python main.py
```

Data goes in `data/vault.db`, a SQLite file created on first run. SQLite is
part of Python itself — there is nothing extra to install and no database to
run.

If you already had a `data/vault.json` from the earlier version, the first
launch imports it and renames it `vault.json.imported`. Nothing is deleted.

## Moving it to another machine

Copy the `.py` files in this folder (`test_vault.py` is optional), run
`pip install customtkinter`, then `python main.py`. To bring the data across,
copy `data/vault.db` too — it is a single self-contained file.

## Using it

- **+ System** — add an application. The two folder fields have a Browse button.
- **ACCESS tab** — add an environment (SIT, UAT, whatever the team calls it),
  give it a URL, then add the accounts. `Open` launches the URL, `user` and
  `pass` copy to the clipboard.
- **PLAN & LOG tab** — one project per test exercise. Tick off the plan, add a
  dated log entry when something happens. Set a project to `done` and start a
  new one next time; the old one stays readable.
- **Status** — `active`, `parked`, `done`. Finished systems collapse into a
  group at the bottom of the list so they stay out of the way.
- Everything saves the moment you change it. There is no Save button.

Follows the system light/dark setting.

Don't run two copies at once. If you do, the second one to save is refused with
a message rather than overwriting the first — but you'll lose whatever that
window had unsaved.

Credentials are stored in plain text. This is a convenience store on one
machine, not a security product.

## If something looks wrong

`vault.db` is SQLite, which means you cannot read it in Notepad. You do not
need any database tool to deal with it — `vault_tool.py` is plain Python:

```
python vault_tool.py info             what is in the vault
python vault_tool.py export           write it out as readable JSON
python vault_tool.py import my.json   put an edited file back
python vault_tool.py backup           date-stamped copy of the vault
```

`export`, edit the JSON in any text editor, `import` — that is the repair
route, and the same way to move data between machines if copying `vault.db`
is ever awkward. `import` backs up the current vault before replacing it.

## Tests

```
python -m pytest test_vault.py
```
