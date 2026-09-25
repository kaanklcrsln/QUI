"""Undo commands. Every theme edit goes through one of these."""

from __future__ import annotations

import copy
import time
import weakref
from typing import TYPE_CHECKING, Any

from ..compat import QUndoCommand

if TYPE_CHECKING:
    from .editor_window import EditorWindow

MERGE_WINDOW_S = 1.0  # consecutive edits of the same property within this merge into one step


class _EditorCommand(QUndoCommand):
    """Holds the editor weakly: the undo stack (owned by the editor) keeps commands alive,
    and a strong reference back would keep the editor's Python wrapper from ever being freed."""

    def __init__(self, editor: EditorWindow, text: str) -> None:
        super().__init__(text)
        self._editor = weakref.ref(editor)

    @property
    def editor(self) -> EditorWindow:
        return self._editor()


class _PropertyCommand(_EditorCommand):
    """Sets one value; merges with the next edit of the same key made soon after."""

    MERGE_ID = -1

    def __init__(self, editor: EditorWindow, key: tuple, old: Any, new: Any, text: str) -> None:
        super().__init__(editor, text)
        self.key = key
        self.old = copy.deepcopy(old)
        self.new = copy.deepcopy(new)
        self.stamp = time.monotonic()
        self._pushed = False

    def id(self) -> int:
        return self.MERGE_ID

    def mergeWith(self, other: QUndoCommand) -> bool:
        if other.id() != self.id() or other.key != self.key or other.stamp - self.stamp > MERGE_WINDOW_S:
            return False
        self.new = other.new
        self.stamp = other.stamp
        return True

    def redo(self) -> None:
        # The first redo happens on push, right after the user made the edit: don't
        # disturb the inspector. Later redos reveal what changed.
        self.apply(self.new, reveal=self._pushed)
        self._pushed = True

    def undo(self) -> None:
        self.apply(self.old, reveal=True)

    def apply(self, value: Any, reveal: bool) -> None:
        raise NotImplementedError


class SetStateValue(_PropertyCommand):
    MERGE_ID = 1

    def apply(self, value: Any, reveal: bool) -> None:
        self.editor.apply_state_value(*self.key, copy.deepcopy(value), reveal=reveal)


class SetGlobalValue(_PropertyCommand):
    MERGE_ID = 2

    def apply(self, value: Any, reveal: bool) -> None:
        self.editor.apply_global_value(self.key[0], copy.deepcopy(value))


class ReplaceTheme(_EditorCommand):
    """Swap the whole theme (presets, bulk edits); stores both as plain dicts."""

    def __init__(self, editor: EditorWindow, before: dict, after: dict, text: str) -> None:
        super().__init__(editor, text)
        self.before = before
        self.after = after

    def redo(self) -> None:
        self.editor.apply_theme_dict(self.after)

    def undo(self) -> None:
        self.editor.apply_theme_dict(self.before)
