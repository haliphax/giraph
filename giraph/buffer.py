"""GraphemeBuffer class"""

# stdlib
from __future__ import annotations
from typing_extensions import SupportsIndex
import unicodedata

# 3rd party
from emoji import is_emoji
from wcwidth import wcswidth  # type: ignore

# local
from . import logger
from .constants import (
    ASSUME_WIDE,
    EMOJI_VS,
    FORCE_EVS_WIDE,
    MODIFIERS,
    VALID_ZWC,
    VARIATION_SELECTORS,
    ZWJ,
    ZWNJ,
)
from .grapheme import Grapheme


class GraphemeBuffer(list[Grapheme | None]):
    """
    A contiguous segment of cells for display on the console, each of which is
    either a `Grapheme` instance or `None`. A value of `None` should denote that
    the cell is occupied by the remainder of the previous `Grapheme` (i.e. the
    previous `Grapheme` has a `width` value greater than 1).
    """

    def __add__(self, __object: str):  # type: ignore
        return GraphemeBuffer(
            super(GraphemeBuffer, self).__add__(
                GraphemeBuffer.from_str(__object)
            )
        )

    def __iadd__(self, __object: str):  # type: ignore
        return super(GraphemeBuffer, self).__iadd__(
            GraphemeBuffer.from_str(__object)
        )

    def __repr__(self):
        return f"GraphemeBuffer({len(self)})"

    def __setitem__(  # type: ignore
        self,
        __index: SupportsIndex,
        __object: str,
    ):
        return super(GraphemeBuffer, self).__setitem__(
            __index, GraphemeBuffer.from_str(__object)[0]
        )

    def __str__(self):
        return "".join(str(g) if g else "" for g in self)

    def append(self, __object: Grapheme | None) -> None:
        val = super().append(__object)

        # pad wide graphemes
        if __object and __object.width > 1:
            for _ in range(__object.width - 1):
                super().append(None)

        return val

    def insert(self, __index: SupportsIndex, __object: Grapheme | None) -> None:
        if not isinstance(__index, int):
            return NotImplemented

        if __object and __object.width > 1:
            for _ in range(__object.width - 1):
                super().insert(__index, None)

        return super().insert(__index, __object)

    def pop(self, __index: SupportsIndex = -1) -> Grapheme | None:
        if not isinstance(__index, int):
            return NotImplemented

        val = super().pop(__index)
        idx = int(__index)

        if val and val.width > 1 and idx >= 0:
            for _ in range(val.width - 1):
                super().pop(__index)

        iterate = idx > 0

        while not val and idx != 0:
            if iterate:
                idx -= 1

            val = super().pop(idx)

        return val

    @property
    def count(self):
        """The total number of `Grapheme` objects, excluding `None` values."""

        return sum([1 if g else 0 for g in self])

    @property
    def raw(self):
        """Console output as a `str` without forced-width adjustments."""

        return "".join(g.raw if g else "" for g in self)

    def _strip(self, lstrip: bool = False) -> GraphemeBuffer:
        length = len(self)

        if length == 0:
            return GraphemeBuffer()

        idx = -1 if lstrip else 0
        limit = length + idx
        step = 1 if lstrip else -1
        grapheme: Grapheme | None = None
        discard = set((" ", "\n"))
        absidx = 0

        while (grapheme is None or grapheme.char in discard) and absidx < limit:
            idx += step
            absidx = abs(idx)
            grapheme = self[idx]

        if not grapheme:
            logger.debug("empty after strip")
            return GraphemeBuffer()

        if not lstrip:
            idx -= step * grapheme.width

        if idx == 0:
            return GraphemeBuffer(self.copy())

        logger.debug(f"stripped: {idx}")
        return GraphemeBuffer(self[idx:] if lstrip else self[:idx])

    def lstrip(self):
        """Trim leading spaces/newlines."""

        return self._strip(True)

    def rstrip(self):
        """Trim trailing spaces/newlines."""

        return self._strip()

    def strip(self):
        """Trim leading and trailing spaces/newlines."""

        return self._strip()._strip(True)

    def split(self, separator: Grapheme | str):
        """
        Split the segment into smaller segments, separated by `separator`.

        Args:
            separator: The `Grapheme` or `str` to use for tokenizing.

        Returns:
            A list of `ConsoleString` instances.
        """

        is_grapheme = isinstance(separator, Grapheme)
        result: list[GraphemeBuffer] = []
        segment = GraphemeBuffer()

        for g in [g for g in self if g]:
            if (is_grapheme and g == separator) or (
                not is_grapheme and g.char == separator
            ):
                result.append(segment)
                segment = GraphemeBuffer()
            else:
                segment.append(g)

        if len(segment):
            result.append(segment)

        return result

    @classmethod
    def from_str(cls, string: str) -> GraphemeBuffer:
        """
        Split a string into (potentially clustered) graphemes.

        Args:
            string: The string to parse.

        Returns:
            A `GraphemeBuffer` instance representing the input string.
        """

        def _append_cell(cell: Grapheme, cells: GraphemeBuffer):
            if cell:
                logger.debug(f"appending {cell!r}")
                cells.append(cell)

            return Grapheme()

        cell = Grapheme()
        cells = GraphemeBuffer()
        joined = False
        was_emoji = False

        for c in string:
            assert cell

            if c == ZWJ:
                if was_emoji:
                    logger.debug("ZWJ")
                    cell.mods.append(c)
                    joined = True
                else:
                    logger.debug("unexpected ZWJ")

                continue

            if c == ZWNJ:
                joined = False

                if cell.char != "":
                    logger.debug(f"ZWNJ{'; end emoji' if was_emoji else ''}")
                    cell.mods.append(c)
                    was_emoji = False
                else:
                    logger.debug("unexpected ZWNJ")

                continue

            if unicodedata.combining(c) != 0:
                if cells:
                    logger.debug(f"combining character: {'o' + c!r}")
                    idx = -1
                    prev: Grapheme | None = None

                    while prev is None and -idx <= len(cells):
                        prev = cells[idx]
                        idx -= 1

                    if prev is None:
                        logger.debug("walk ended unexpectedly")
                    else:
                        prev.mods.append(c)
                        cell = Grapheme()
                else:
                    logger.debug("unexpected combining character")

                continue

            if c in VARIATION_SELECTORS:
                logger.debug(f"variation selector: 0x{ord(c):04X}")

                if cell.char == "":
                    next_cell = cells.pop()
                    assert next_cell
                    cell = next_cell

                if c == EMOJI_VS:
                    logger.debug("emoji VS")
                    was_emoji = True

                    if FORCE_EVS_WIDE and cell.width < 2:
                        logger.debug("forced wide")
                        cell.width = 2
                        cell.force_width = True

                cell.mods.append(c)
                continue

            if c in MODIFIERS:
                logger.debug(f"base modifier: {c!r}")

                if cell.char != "":
                    cell.mods.append(c)
                else:
                    cell.char = c

                if not is_emoji(cell.raw):
                    # separate modifier from emoji if invalid
                    logger.debug(f"invalid base: {cell!r}")

                    if cell.mods:
                        cell.mods.pop()

                    cell.mods.append(ZWNJ)
                    cell = _append_cell(cell, cells)
                else:
                    was_emoji = True
                    continue

            if joined:
                logger.debug(f"joining: {c!r}")
                cell.mods += c
                joined = False
                continue

            if cell.char != "":
                cell = _append_cell(cell, cells)

            if unicodedata.east_asian_width(c) == "W":
                logger.debug("wide")
                cell.width = 2
            else:
                cell.width = wcswidth(c)

            # assume the terminal will cause a problematic visual column offset
            # when displaying emoji that are (incorrectly) labeled as Narrow
            if ASSUME_WIDE and was_emoji and cell.width < 2:
                logger.debug("assumed wide")
                cell.width = 2
                cell.force_width = True

            if is_emoji(c):
                logger.debug(f"emoji: {c!r}")
                cell.char = c
                was_emoji = True
                continue

            if was_emoji:
                logger.debug("end emoji")
                idx = -1
                lookback: Grapheme | None = None

                while lookback is None and -idx <= len(cells):
                    lookback = cells[idx]
                    idx -= 1

                if lookback is None:
                    logger.debug("walk ended unexpectedly")
                elif not is_emoji(str(lookback).rstrip().rstrip(EMOJI_VS)):
                    logger.debug(f"invalid emoji: {lookback!r}")
                    # strip all but base emoji character if invalid
                    lookback.mods.clear()

            was_emoji = False

            if wcswidth(c) < 1:
                hexstr = f"0x{ord(c):04X}"

                if c not in VALID_ZWC:
                    logger.debug(f"stripping ZWC: {hexstr}")
                    continue

                logger.debug(f"ZWC: {hexstr}")

            cell.char = c
            cell = _append_cell(cell, cells)

        return cells
