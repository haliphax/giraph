"""`Grapheme` class module"""

# stdlib
from __future__ import annotations
import unicodedata

# 3rd party
from wcwidth import wcswidth  # type: ignore


class Grapheme:
    """
    Class for storing (potentially clustered) graphemes

    The base character is stored separately from its various modifying
    sequences to accommodate terminals which do not support zero-width
    characters, combining characters, etc. Variation-selected emoji which are
    considered by the terminal (incorrectly) to be narrow graphemes are flagged
    so that the column offset caused during display can be compensated for.
    """

    char: str
    """Base character"""

    mods: list[str]
    """Modifiers"""

    width: int
    """Character width"""

    force_wide: bool
    """Force 'wide' representation"""

    def __init__(
        self,
        char: str = "",
        mods: list[str] | None = None,
        width: int = 1,
        force_wide: bool = False,
    ):
        self.char = char
        self.mods = mods if mods else []
        self.width = width
        self.force_wide = force_wide

    def _modstr(self, s) -> str:
        return "0x%04X" % ord(s) if wcswidth(s) <= 0 else s

    def __eq__(self, __object: object) -> bool:
        if not isinstance(__object, Grapheme):
            return NotImplemented

        return str(self) == str(__object)

    def __repr__(self) -> str:
        return (
            f"Grapheme(char={unicodedata.name(self.char)}, "
            f"mods=[{', '.join([unicodedata.name(c) for c in self.mods])}], "
            f"width={self.width}{' <forced>' if self.force_wide else ''})"
        )

    def __str__(self) -> str:
        return "".join((self.raw, " " if self.force_wide else ""))

    @property
    def raw(self) -> str:
        """The raw output of this grapheme, without forced-width adjustment."""

        return "".join((self.char, "".join(self.mods)))

    @classmethod
    def from_str(self, input: str) -> Grapheme:
        """
        Construct a single `Grapheme` from the given `str`.

        Args:
            input: The input to parse.

        Returns:
            A `Grapheme` instance representing the first grapheme from the
            input.
        """

        # avoid circular import
        from ._from_str import _from_str

        output = _from_str(input, True)
        assert isinstance(output, Grapheme)
        return output
