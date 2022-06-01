#!/usr/bin/env python3

# somafm.py - SomaFM player in Python
# Copyright (C) 2022  Gokberk Yaltirakli

# This is free and unencumbered software released into the public domain.
#
# Anyone is free to copy, modify, publish, use, compile, sell, or
# distribute this software, either in source code form or as a compiled
# binary, for any purpose, commercial or non-commercial, and by any
# means.
#
# In jurisdictions that recognize copyright laws, the author or authors
# of this software dedicate any and all copyright interest in the
# software to the public domain. We make this dedication for the benefit
# of the public at large and to the detriment of our heirs and
# successors. We intend this dedication to be an overt act of
# relinquishment in perpetuity of all present and future rights to this
# software under copyright law.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

import time
import urllib.request
import os

try:
    import PySimpleGUI as sg
except Exception:
    print("Cannot find PySimpleGUI, fetching...")
    path = os.path.dirname(os.path.realpath(__file__))
    url = (
        "https://raw.githubusercontent.com"
        "/PySimpleGUI/PySimpleGUI/master/PySimpleGUI.py"
    )
    with open(f"{path}/PySimpleGUI.py", "wb+") as f:
        req = urllib.request.urlopen(url)
        f.write(req.read())
    print("Done")
    import PySimpleGUI as sg

import xml.etree.ElementTree as ET
import subprocess
import threading
import random
from collections import namedtuple

PLAYERS = [
    ["mpv", "--no-video"],
    ["ffplay", "-nodisp"],
    ["cvlc"],
    ["vlc"],
]

def find_stream_from_pls(url):
    r = urllib.request.urlopen(url)
    for line in r:
        try:
            line = line.strip().decode("ascii")
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key == "File1":
                return value
        except Exception:
            pass

def play_url(url):
    stream = find_stream_from_pls(url)
    for executable in PLAYERS:
        try:
            p = subprocess.Popen(
                (*executable, stream),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return p
        except Exception:
            pass


Channel = namedtuple("Channel", "id title genres listeners dj slowpls")


def fetch_channel_list():
    channels = []

    url = "https://somafm.com/channels.xml"
    text = urllib.request.urlopen(url).read()

    root = ET.fromstring(text)

    for chan in root.findall("channel"):
        ch = Channel(
            chan.get("id"),
            chan.find("title").text,
            chan.find("genre").text.split("|"),
            int(chan.find("listeners").text),
            chan.find("dj").text or "",
            chan.find("slowpls").text,
        )
        channels.append(ch)

    channels.sort(key=lambda x: x.listeners, reverse=True)
    return channels


def channel_table():
    table = []

    for channel in channel_list:
        table.append(
            (
                channel.id,
                channel.title,
                str(channel.listeners),
                ", ".join(channel.genres),
                channel.dj,
            )
        )

    return table


def total_listeners():
    return sum([x.listeners for x in channel_list])


channel_list = fetch_channel_list()


def _():
    while True:
        time.sleep(random.randint(30, 60))
        try:
            globals()["channel_list"] = fetch_channel_list()
        except Exception:
            pass


threading.Thread(target=_, daemon=True).start()


sg.theme("DarkAmber")

window = sg.Window(
    "SomaFM",
    right_click_menu=[
        "",
        [
            "Refresh",
            "Stop audio",
            "Random station",
            "Random station (weighted)",
            "Exit application",
        ],
    ],
)
player = None

window.add_row(
    (
        sg.Text("There are"),
        totalListeners := sg.Text(str(total_listeners())),
        sg.Text("people listening to SomaFM right now."),
    )
)

window.add_row(
    (
        sg.Button("Exit application"),
        stopButton := sg.Button("Stop audio", visible=False),
    )
)

window.add_row(
    (
        _channel_table := sg.Table(
            channel_table(),
            headings=("ID", "Title", "Listeners", "Genre", "DJ"),
            bind_return_key=True,
            key="channelTable",
            visible_column_map=[False, True, True, True, True],
            max_col_width=50,
        )
    )
)

window.add_row(
    (
        sg.Text("Enjoy SomaFM? Consider donating."),
        sg.Button("Donate"),
    )
)

window.finalize()
window.move_to_center()


def play_channel(ch):
    global player
    window.set_title(f"SomaFM - {ch.title}")

    try:
        player.terminate()
    except Exception:
        pass
    player = play_url(ch.slowpls)


try:
    while True:
        event, values = window.read(timeout=100)

        if event == "__TIMEOUT__":
            totalListeners.update(value=str(total_listeners()))

            try:
                assert player.poll() is None
                stopButton.update(visible=True)
            except Exception:
                stopButton.update(visible=False)
                window.set_title("SomaFM")
            continue

        if event in (sg.WIN_CLOSED, "Exit application"):
            break

        if event == "Stop audio":
            try:
                player.terminate()
                player = None
            except Exception:
                pass

        if event == "channelTable":
            ct = values["channelTable"]
            if ct:
                index = ct[0]
                ch = channel_list[index]
                play_channel(ch)

        if event == "Random station":
            play_channel(random.choice(channel_list))

        if event == "Random station (weighted)":
            chans = list(channel_list)
            total = sum([x.listeners for x in chans])
            r = random.randint(0, total)
            for c in chans:
                if r > c.listeners:
                    r -= c.listeners
                    continue
                play_channel(c)
                break

        if event == "Donate":
            import webbrowser

            webbrowser.open("https://somafm.com/support/")

        _channel_table.update(values=channel_table())
except Exception:
    pass

try:
    player.terminate()
except Exception:
    pass
window.close()
