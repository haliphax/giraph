"""`GraphemeBuffer` class module"""

# stdlib
from __future__ import annotations
from typing_extensions import SupportsIndex

# local
from .logging import logger
from .grapheme import Grapheme


class GraphemeBuffer(list[Grapheme | None]):
    """
    A contiguous segment of cells for display on the console, each of which is
    either a `Grapheme` instance or `None`. A value of `None` should denote that
    the cell is occupied by the remainder of the previous `Grapheme` (i.e. the
    previous `Grapheme` has a `width` value greater than 1).
    """

    def __add__(self, __object: str) -> GraphemeBuffer:  # type: ignore
        return GraphemeBuffer(
            super(GraphemeBuffer, self).__add__(
                GraphemeBuffer.from_str(__object)
            )
        )

    def __iadd__(self, __object: str) -> GraphemeBuffer:  # type: ignore
        return super(GraphemeBuffer, self).__iadd__(
            GraphemeBuffer.from_str(__object)
        )

    def __repr__(self) -> str:
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
        val = super(GraphemeBuffer, self).append(__object)

        # pad wide graphemes
        if __object and __object.width > 1:
            for _ in range(__object.width - 1):
                super(GraphemeBuffer, self).append(None)

        return val

    def insert(self, __index: SupportsIndex, __object: Grapheme | None) -> None:
        if not isinstance(__index, int):
            return NotImplemented

        if __object and __object.width > 1:
            for _ in range(__object.width - 1):
                super(GraphemeBuffer, self).insert(__index, None)

        return super(GraphemeBuffer, self).insert(__index, __object)

    def pop(self, __index: SupportsIndex = -1) -> Grapheme | None:
        if not isinstance(__index, int):
            return NotImplemented

        val = super(GraphemeBuffer, self).pop(__index)
        idx = int(__index)

        if val and val.width > 1 and idx >= 0:
            for _ in range(val.width - 1):
                super(GraphemeBuffer, self).pop(__index)

        iterate = idx > 0

        while not val and idx != 0:
            if iterate:
                idx -= 1

            val = super(GraphemeBuffer, self).pop(idx)

        return val

    @property
    def grapheme_count(self) -> int:
        """The total number of `Grapheme` objects, excluding `None` values."""

        return sum([1 if g else 0 for g in self])

    @property
    def raw(self) -> str:
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

    def lstrip(self) -> GraphemeBuffer:
        """Trim leading spaces/newlines."""

        return self._strip(True)

    def rstrip(self) -> GraphemeBuffer:
        """Trim trailing spaces/newlines."""

        return self._strip()

    def strip(self) -> GraphemeBuffer:
        """Trim leading and trailing spaces/newlines."""

        return self._strip()._strip(True)

    def split(self, separator: Grapheme | str) -> list[GraphemeBuffer]:
        """
        Split the segment into smaller segments, separated by `separator`.

        Args:
            separator: The `Grapheme` or `str` to use for tokenizing.

        Returns:
            A list of `GraphemeBuffer` instances.
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
    def from_str(cls, input: str) -> GraphemeBuffer:
        """
        Construct a `GraphemeBuffer` from the given `str`.

        Args:
            input: The input to parse.

        Returns:
            A `GraphemeBuffer` instance representing the grapheme(s) from the input.
        """

        # avoid circular import
        from ._from_str import _from_str

        output = _from_str(input, False)
        assert isinstance(output, GraphemeBuffer)
        return output
