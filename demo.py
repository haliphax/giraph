"""Giraph demonstration script"""

# local
from giraph import GraphemeBuffer, logger
from giraph.constants import EMOJI_VS, ZWJ, ZWNJ


# imperfections in raw string are intentional to demonstrate split/strip
out_demo_data = f"""    \nemoji:
------
🎨 - standard wide
♂{EMOJI_VS} - variation-selected narrow
🏿 - skin tone solo
👋🏾 - skin tone 👋{ZWNJ}🏾
🧑‍💻 - zero-width-joiner 🧑💻   \n😭{ZWJ}🚒 - invalid zwj 😭🚒
👨‍👩‍👧 - multiple zwj 👨👩👧
🧙‍♂️ - zwj + evs narrow 🧙♂{EMOJI_VS}
🧑🏼‍🚒 - skin tone 🧑{ZWNJ}🏼, zwj 🚒
👮🏿‍♀️ - skin tone 👩{ZWNJ}🏿, multiple zwj + evs narrow 👮♀{EMOJI_VS}
     ^
     all descriptions should line up here

combining characters:
---------------------
a - standard narrow
â - narrow + combining character
    ^
    all descriptions should line up here

undefined behavior:
-------------------
😭🏿 - invalid modifier base (emoji)
x🏿 - invalid modifier base (non-emoji)
😭̂ - invalid combiner base
"""
out_demo_str = GraphemeBuffer.from_str(out_demo_data)
out_demo_grid = out_demo_str.split("\n")
out_demo_stripped: list[GraphemeBuffer] = []

for row in out_demo_grid:
    logger.debug(repr(row))

    for g in row:
        logger.debug(f"  {repr(g)}")

    stripped = row.rstrip()
    out_demo_stripped.append(stripped)

print(repr(out_demo_str))

for row in out_demo_stripped:
    print(row)

logger.debug("")

# metadata demo (len vs. count, show items)

md_demo_str = "👩🏽‍💻\nxx"
md_demo = GraphemeBuffer.from_str(md_demo_str)
md_demo_split = md_demo.split("\n")
md_demo_output = f"""
{md_demo}
- str: {repr(md_demo_str)}
- split:
"""

print(md_demo_output, end="")

for row in md_demo_split:
    print(f"  - {repr(row)} {row.grapheme_count} grapheme(s)")

    for g in row:
        print(f"    - {repr(g)}")
