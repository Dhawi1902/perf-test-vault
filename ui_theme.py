"""Shared colours and button styles.

Every colour is a (light, dark) pair so the app stays readable in both modes.
CustomTkinter's default button text is near-white in both, which disappears on
a transparent button in light mode -- hence outline_button below.
"""

from __future__ import annotations

import customtkinter as ctk

MUTED = ("gray45", "gray60")
CARD = ("gray93", "gray21")
DANGER = ("#b3261e", "#f2b8b5")

# Plan item states. Each is a (light, dark) pair so chips stay legible.
STATE_COLORS = {
    "todo": ("gray60", "gray45"),
    "doing": ("#1f6aa5", "#2d7dc4"),
    "waiting": ("#a86a1f", "#c98a2e"),
    "done": ("#2f7d4f", "#3c9b63"),
}
STATE_LABELS = {"todo": "to do", "doing": "doing", "waiting": "waiting", "done": "done"}

_OUTLINE_TEXT = ("gray20", "gray90")
_OUTLINE_BORDER = ("gray65", "gray40")
_OUTLINE_HOVER = ("gray85", "gray28")


def outline_button(parent, text: str, command, width: int = 56, height: int = 24,
                   danger: bool = False, **kwargs) -> ctk.CTkButton:
    """A bordered, see-through button that is legible in light and dark."""
    return ctk.CTkButton(
        parent, text=text, command=command, width=width, height=height,
        fg_color="transparent", border_width=1, border_color=_OUTLINE_BORDER,
        text_color=DANGER if danger else _OUTLINE_TEXT,
        hover_color=_OUTLINE_HOVER, **kwargs)


def heading(parent, text: str) -> ctk.CTkLabel:
    return ctk.CTkLabel(parent, text=text, anchor="w", text_color=MUTED,
                        font=ctk.CTkFont(size=11, weight="bold"))


def state_chip(parent, state: str, command) -> ctk.CTkButton:
    """A small coloured button showing a plan item's state; click to advance."""
    return ctk.CTkButton(parent, text=STATE_LABELS[state], command=command,
                         width=64, height=24, corner_radius=12,
                         fg_color=STATE_COLORS[state], hover=False,
                         text_color=("white", "white"),
                         font=ctk.CTkFont(size=11, weight="bold"))
