"""`str` to `Grapheme` and `GraphemeBuffer` conversion"""

# stdlib
from __future__ import annotations
from typing import TYPE_CHECKING
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

if TYPE_CHECKING:
    from .buffer import GraphemeBuffer
    from .grapheme import Grapheme


def _from_str(input: str, stop_at_first: bool) -> GraphemeBuffer | Grapheme:
    def _append_cell(cell: Grapheme, cells: GraphemeBuffer):
        if cell:
            logger.debug(f"appending {cell!r}")
            cells.append(cell)

        return Grapheme()

    cell = Grapheme()
    cells = GraphemeBuffer()
    joined = False
    was_emoji = False

    for c in input:
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
                    cell.force_wide = True

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
            cell.force_wide = True

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

        if stop_at_first:
            return cell

        cell = _append_cell(cell, cells)

    return cells


def grapheme_from_str(input: str) -> Grapheme:
    """
    Construct a single `Grapheme` from the given `str`.

    Args:
        input: The input to parse.

    Returns:
        A `Grapheme` instance representing the first grapheme from the
        input.
    """

    output = _from_str(input, True)
    assert isinstance(output, Grapheme)
    return output


def grapheme_buffer_from_str(input: str) -> GraphemeBuffer:
    """
    Construct a `GraphemeBuffer` from the given `str`.

    Args:
        input: The input to parse.

    Returns:
        A `GraphemeBuffer` instance representing the grapheme(s) from the input.
    """

    output = _from_str(input, False)
    assert isinstance(output, GraphemeBuffer)
    return output
