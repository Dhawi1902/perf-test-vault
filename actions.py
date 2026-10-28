"""Things the app does to the world outside itself: clipboard, Explorer, browser."""

from __future__ import annotations

import os
import subprocess
import sys
import webbrowser
from pathlib import Path


def copy(widget, value: str) -> bool:
    """Put text on the clipboard. Returns False if there was nothing to copy."""
    if not value:
        return False
    widget.clipboard_clear()
    widget.clipboard_append(value)
    widget.update_idletasks()
    return True


def open_url(url: str) -> tuple[bool, str]:
    if not url:
        return False, "no URL set"
    target = url if "://" in url else f"https://{url}"
    try:
        webbrowser.open(target)
    except OSError as exc:
        return False, str(exc)
    return True, ""


def open_folder(raw_path: str) -> tuple[bool, str]:
    """Open a folder in the system file manager."""
    if not raw_path:
        return False, "no folder set"
    path = Path(raw_path)
    if not path.exists():
        return False, f"folder not found:\n{path}"
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=True)
        else:
            subprocess.run(["xdg-open", str(path)], check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        return False, str(exc)
    return True, ""


def folder_exists(raw_path: str) -> bool:
    return bool(raw_path) and Path(raw_path).exists()
