#!/usr/bin/env python3
from collections import namedtuple
from typing import Union
import math

# generate-vim-colorscheme.py: Generate a vim colorscheme with Python code
# Gokberk Yaltirakli, 2022

# This script generates a vim colorscheme file that maps the colors used to
# their closest 256-color terminal equivalent.

Color = namedtuple("Color", "r g b")

# The following colors are from the default 256-color palette

term_colors = {}
term_colors[0] = Color(0, 0, 0)
term_colors[1] = Color(128, 0, 0)
term_colors[2] = Color(0, 128, 0)
term_colors[3] = Color(128, 128, 0)
term_colors[4] = Color(0, 0, 128)
term_colors[5] = Color(128, 0, 128)
term_colors[6] = Color(0, 128, 128)
term_colors[7] = Color(192, 192, 192)
term_colors[8] = Color(128, 128, 128)
term_colors[9] = Color(255, 0, 0)
term_colors[10] = Color(0, 255, 0)
term_colors[11] = Color(255, 255, 0)
term_colors[12] = Color(0, 0, 255)
term_colors[13] = Color(255, 0, 255)
term_colors[14] = Color(0, 255, 255)
term_colors[15] = Color(255, 255, 255)
term_colors[16] = Color(0, 0, 0)
term_colors[17] = Color(0, 0, 95)

term_colors[59] = Color(95, 95, 95)
term_colors[60] = Color(95, 95, 135)
term_colors[101] = Color(135, 135, 95)
term_colors[102] = Color(135, 135, 135)
term_colors[103] = Color(135, 135, 175)
term_colors[145] = Color(175, 175, 175)
term_colors[153] = Color(175, 215, 255)
term_colors[188] = Color(215, 215, 215)

term_colors[231] = Color(255, 255, 255)
term_colors[232] = Color(8, 8, 8)
term_colors[233] = Color(18, 18, 18)
term_colors[234] = Color(28, 28, 28)
term_colors[235] = Color(38, 38, 38)
term_colors[236] = Color(48, 48, 48)
term_colors[237] = Color(58, 58, 58)
term_colors[238] = Color(68, 68, 68)
term_colors[239] = Color(78, 78, 78)
term_colors[240] = Color(88, 88, 88)
term_colors[241] = Color(98, 98, 98)
term_colors[242] = Color(108, 108, 108)
term_colors[243] = Color(118, 118, 118)
term_colors[244] = Color(128, 128, 128)
term_colors[245] = Color(138, 138, 138)
term_colors[246] = Color(148, 148, 148)
term_colors[247] = Color(158, 158, 158)
term_colors[248] = Color(168, 168, 168)
term_colors[249] = Color(178, 178, 178)
term_colors[250] = Color(188, 188, 188)
term_colors[251] = Color(198, 198, 198)
term_colors[252] = Color(208, 208, 208)
term_colors[253] = Color(218, 218, 218)
term_colors[254] = Color(228, 228, 228)
term_colors[255] = Color(238, 238, 238)


def color_distance(c1: Color, c2: Color) -> float:
    """Compute the distance between two colors.
    
    This is the Euclidean distance in RGB space.

    Parameters
    ----------
    c1 : Color
        The first color
    c2 : Color
        The second color

    Returns
    -------
    float
        The distance between the two colors.
    """
    x = 0
    x += (c1.r - c2.r) ** 2
    x += (c1.g - c2.g) ** 2
    x += (c1.b - c2.b) ** 2
    return math.sqrt(x)


def grayscale(x: int) -> Color:
    """Return a grayscale color with the given intensity.
    
    The intensity is a value between 0 and 100.

    Parameters
    ----------
    x : int
        The intensity of the color.

    Returns
    -------
    Color
        The grayscale color.
    """
    assert x >= 0 and x <= 100
    f = x / 100
    y = int(f * 255)
    return Color(y, y, y)


def find_term_index(color: Color) -> int:
    for key in term_colors:
        if term_colors[key] == color:
            return key
    raise AssertionError("Cannot turn color into terminal index")


def find_closest(color: Color) -> Color:
    def key(x):
        return color_distance(color, x)

    return min(term_colors.values(), key=key)


def color_to_hex(color: Color) -> str:
    triplet = (color.r, color.g, color.b)
    hex_triplet = map(lambda x: x.to_bytes(1, "big").hex(), triplet)
    str_triplet = "".join(hex_triplet)
    return f"#{str_triplet}"


def highlight(
    name: str,
    attr: str,
    fg_color: Union[Color, None],
    bg_color: Union[Color, None],
) -> str:
    if fg_color:
        fg_closest = find_closest(fg_color)
        fg_term_index = str(find_term_index(fg_closest))
        fg_color_hex = color_to_hex(fg_closest)
    else:
        fg_term_index = "NONE"
        fg_color_hex = "NONE"

    if bg_color:
        bg_closest = find_closest(bg_color)
        bg_term_index = str(find_term_index(bg_closest))
        bg_color_hex = color_to_hex(bg_closest)
    else:
        bg_term_index = "NONE"
        bg_color_hex = "NONE"

    if not attr:
        attr = "NONE"

    line = f"hi {name} term={attr} cterm={attr} ctermfg={fg_term_index} ctermbg={bg_term_index} gui={attr} guifg={fg_color_hex} guibg={bg_color_hex}"
    print(line)
    return line

# Vim colorscheme boilerplate
print("highlight clear")
print("set background=dark")
print("syntax reset")

highlight("Normal", "", grayscale(50), grayscale(0))

highlight("ModeMsg", "", Color(30, 200, 30), grayscale(10))
highlight("StatusLine", "", grayscale(5), grayscale(70))
highlight("LineNr", "", grayscale(70), None)
highlight("CursorLineNr", "bold", grayscale(100), grayscale(10))
highlight("CursorLine", "underline", None, None)
highlight("ColorColumn", "", None, grayscale(15))

highlight("Include", "", grayscale(50), None)
highlight("Statement", "bold", grayscale(55), None)

highlight("pythonInclude", "bold", grayscale(55), None)

highlight("Identifier", "", grayscale(70), None)
highlight("Type", "", grayscale(70), None)
highlight("Special", "italic", grayscale(70), None)
highlight("Function", "", grayscale(50), None)
highlight("PreProc", "", grayscale(50), None)

highlight("Comment", "italic", grayscale(95), None)
highlight("MatchParen", "bold", grayscale(100), None)
highlight("String", "italic", grayscale(70), None)
highlight("Constant", "", grayscale(50), None)
highlight("Cursor", "reverse", None, None)
highlight("TermCursor", "reverse", None, None)

highlight("Todo", "", grayscale(0), Color(200, 200, 50))
