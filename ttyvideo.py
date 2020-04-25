#!/usr/bin/env python3
from PIL import Image, ImageDraw, ImageFont
import fcntl
import os
import pty
import select
import struct
import sys
import termios
import time
import numpy as np
from collections import namedtuple

std_colors = [
    (0, 0, 0),  # Black
    (194, 54, 33),  # Red
    (37, 188, 36),  # Green
    (173, 173, 39),  # Yellow
    (73, 46, 225),  # Blue
    (211, 56, 211),  # Magenta
    (51, 187, 200),  # Cyan
    (203, 204, 205),  # White
    (129, 131, 131),  # Bright black
    (252, 57, 31),  # Bright red
    (49, 231, 34),  # Bright green
    (234, 236, 35),  # Bright yellow
    (88, 51, 255),  # Bright blue
    (249, 53, 248),  # Bright magenta
    (20, 240, 240),  # Bright cyan
    (233, 235, 235),  # Bright white
]

for r in range(6):
    for g in range(6):
        for b in range(6):
            r = int(np.interp(r, [0, 5], [0, 255]))
            g = int(np.interp(g, [0, 5], [0, 255]))
            b = int(np.interp(b, [0, 5], [0, 255]))
            std_colors.append((r, g, b))

for v in range(24):
    v = int(np.interp(v, [0, 23], [0, 255]))
    std_colors.append((v, v, v))


class VirtualTerminal:
    def __init__(self, rows=30, cols=80):
        self.__rows = rows
        self.__cols = cols

        self.__foreground = (255, 255, 255)
        self.__background = (0, 0, 0)

        self.__scrbuf = [
            ("", self.__foreground, self.__background)
            for _ in range(rows * cols)
        ]

        self.__row = 0
        self.__col = 0

        self.__state = ""
        self.__statebuf = ""

    def __get_index(self, x, y):
        return y * self.__cols + x

    def __scroll(self):
        if self.__row >= self.__rows:
            for y in range(self.__rows - 1):
                for x in range(self.__cols):
                    index = self.__get_index(x, y)
                    index_old = self.__get_index(x, y + 1)
                    self.__scrbuf[index] = self.__scrbuf[index_old]

            # Clear last line
            for x in range(self.__cols):
                index = self.__get_index(x, self.__rows - 1)
                self.__scrbuf[index] = (
                    " ",
                    self.__foreground,
                    self.__background,
                )
            self.__row -= 1

    def __write_char(self, c):
        if c == "\n":
            self.__col = 0
            self.__row += 1
            self.__scroll()
            return

        if c == "\r":
            self.__col = 0
            return

        index = self.__get_index(self.__col, self.__row)
        self.__scrbuf[index] = (c, self.__foreground, self.__background)
        self.__col += 1

        if self.__col == self.__cols:
            self.__col = 0
            self.__row += 1
            if self.__row == self.__rows:
                self.__row = self.__rows - 1

    def __handle_escape(self, c):
        if c == "[":
            self.__state = "csi"
        else:
            self.__state = ""

    def __handle_csi(self, c):
        unhandled = False

        if c == "A":
            n = 1
            try:
                n = int(self.__statebuf)
            except:
                pass
            self.__row -= n
            self.__row = max(0, self.__row)
        elif c == "C":
            # Move cursor forward
            try:
                self.__col += int(self.__statebuf)
            except:
                self.__col += 1
        elif c == "H":
            # Move cursor to absolute
            parts = self.__statebuf.split(";")

            x = 1
            y = 1

            try:
                self.__row = int(parts.pop(0)) - 1
                self.__col = int(parts.pop(0)) - 1
            except:
                pass
        elif c == "J":
            # Erase in display
            n = int(self.__statebuf if self.__statebuf else "0")
            r = None
            cursor = self.__get_index(self.__col, self.__row)
            if n == 0:
                r = range(cursor, len(self.__scrbuf))
            elif n == 1:
                r = range(cursor, -1, -1)
            elif n == 2:
                r = range(0, len(self.__scrbuf))
                self.__col = 0
                self.__row = 0
            for index in r:
                self.__scrbuf[index] = (
                    " ",
                    self.__foreground,
                    self.__background,
                )

        elif c == "K":
            # Erase in line
            n = int(self.__statebuf if self.__statebuf else "0")
            r = None
            if n == 0:
                r = range(self.__col, self.__cols)
            elif n == 1:
                r = range(self.__col, -1, -1)
            elif n == 2:
                r = range(0, self.__cols)
            for x in r:
                index = self.__get_index(x, self.__row)
                self.__scrbuf[index] = (
                    " ",
                    self.__foreground,
                    self.__background,
                )
        elif c == "m":
            # Style
            attributes = map(
                int, filter(lambda x: x, self.__statebuf.split(";"))
            )
            attributes = list(attributes)
            while attributes:
                attr = attributes.pop(0)
                if attr == 0:
                    self.__foreground = (255, 255, 255)
                    self.__background = (0, 0, 0)
                elif attr == 38:
                    # Set foreground color
                    input_type = attributes.pop(0)
                    if input_type == 2:
                        r = attributes.pop(0)
                        g = attributes.pop(0)
                        b = attributes.pop(0)
                        self.__foreground = (r, g, b)
                    elif input_type == 5:
                        index = attributes.pop(0)
                        self.__foreground = std_colors[index]
                elif attr >= 30 and attr <= 37:
                    self.__foreground = std_colors[attr - 30]
                elif attr == 48:
                    # Set background color
                    input_type = attributes.pop(0)
                    if input_type == 2:
                        r = attributes.pop(0)
                        g = attributes.pop(0)
                        b = attributes.pop(0)
                        self.__background = (r, g, b)
                    elif input_type == 5:
                        index = attributes.pop(0)
                        self.__background = std_colors[index]
        else:
            unhandled = True

        self.__col = max(0, min(self.__col, self.__cols))
        self.__row = max(0, min(self.__row, self.__rows))

        self.__statebuf += c

        if ord(c) > 0x40 and ord(c) < 0x7E:
            if unhandled or True:
                sys.stderr.write(f"CSI {self.__statebuf}\n")
            self.__state = ""
            self.__statebuf = ""

    def write_char(self, c):
        if ord(c) == 0x1B:
            self.__state = "escape"
            return

        if self.__state == "escape":
            self.__handle_escape(c)
            return

        if self.__state == "csi":
            self.__handle_csi(c)
            return

        self.__write_char(c)

    def render(self, scale=2):
        img = Image.new(
            "RGB", (self.__cols * 8 * scale, self.__rows * 16 * scale)
        )
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype(
            font="/usr/share/fonts/gnu-free/FreeMono.otf", size=10 * scale
        )
        x = 0
        y = 0
        for row in range(self.__rows):
            for col in range(self.__cols):
                index = self.__get_index(col, row)
                c = self.__scrbuf[index]
                # sys.stderr.write(f"{x}, {y}, {row}, {col}, {c}\n")
                draw.rectangle([x, y, x + 8 * scale, y + 16 * scale], fill=c[2])
                if row == self.__row and col == self.__col:
                    draw.rectangle(
                        [x, y, x + 8 * scale, y + 13 * scale],
                        fill=(180, 180, 180),
                    )
                draw.text((x, y), c[0], fill=c[1], font=font)
                x += 8 * scale
            x = 0
            y += 16 * scale
        return img


class VirtualTty:
    def __init__(self, rows=30, cols=80):
        self.fd = None
        self.rows = rows
        self.cols = cols
        self.term = VirtualTerminal(rows, cols)

    def __set_winsize(self, fd, row, col, xpix=0, ypix=0):
        winsize = struct.pack("HHHH", row, col, xpix, ypix)
        fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)

    def spawn(self, argv="/bin/sh"):
        assert self.fd is None
        pid, self.fd = pty.fork()

        if pid == pty.CHILD:
            os.execv(argv, [argv])
        else:
            self.__set_winsize(self.fd, self.rows, self.cols)

    def tick(self):
        r, _, _ = select.select([self.fd], [], [], 0)
        if len(r):
            try:
                r = os.read(self.fd, 2048)
                if not r:
                    return False
                for c in r:
                    self.term.write_char(chr(c))
            except Exception as e:
                sys.stderr.write(f"{e}\n")
        return True


def input_events(f):
    t = 0.0
    delay = 0.1

    def typechar(char):
        nonlocal t
        for c in char:
            yield t, c
        t += delay

    def typestr(line):
        for char in line:
            yield from typechar(char)

    for line in f:
        line = line[:-1]
        cmd, *content = line.split(" ", 1)
        cmd = cmd.upper()
        content = content[0] if len(content) else ""

        if cmd == "TL":
            yield from typestr(content)
            yield from typechar("\n")
        elif cmd == "TT":
            yield from typestr(content)
        elif cmd == "ES":
            yield from typechar("\x1b")
        elif cmd == "DL":
            t += float(content)
            yield t, ""
        elif cmd == "SD":
            delay = float(content)
        elif cmd == "UP":
            yield from typechar("\x1b\x5b\x41")
        elif cmd == "DN":
            yield from typechar("\x1b\x5b\x42")
        elif cmd == "RT":
            yield from typechar("\x1b\x5b\x43")
        elif cmd == "LF":
            yield from typechar("\x1b\x5b\x44")


if __name__ == "__main__":
    FPS = 30
    t = 0

    vt = VirtualTty()
    vt.spawn()

    stdout = open("/dev/stdout", "wb")
    with open(sys.argv[1]) as f:
        for until, c in input_events(f):
            while t < until:
                if not vt.tick():
                    sys.exit(1)
                vt.term.render(scale=2).save(stdout, "PNG")
                t += 1.0 / FPS
            os.write(vt.fd, bytes(c, "utf-8"))
