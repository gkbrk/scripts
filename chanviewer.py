#!/usr/bin/env python3

# ChanViewer: Imageboard client application
# Copyright (C) 2020  Gokberk Yaltirakli
#
# ChanViewer is copyrighted free software by Gokberk Yaltirakli. You are
# permitted to redistribute and/or modify it provided that the following
# conditions are met.
#
# 1. Distribution of the software, including any modifications that you create
# or to which you contribute, must be under the terms of this license. You may
# not attempt to alter or restrict the recipients' rights in the source code.
#
# 2. You may make and give away verbatim copies of the source code of the
# software without restriction, provided that you duplicate all of the original
# copyright notices, associated disclaimers and the full license text.
#
# 3. You must provide a copy of the source code, including any modifications
# that you may have created or contributed to, to any recipient of the software
# free of charge. Any such copies must be provided to the recipient under the
# terms of this license.
#
# 4. The rights granted under this license will terminate automatically if you
# fail to comply with any of its terms. Should this happen, you will no longer
# be permitted to use, modify, and/or distribute the softare unless you make
# other distribution arrangements with the author.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

################################################################################
# Program help document
################################################################################
#
# 1. ChanViewer
#
# 1.1. What?
#
#    ChanViewer is an imageboard client written in Python using the GTK3 GUI
#    framework.
#
# 1.2. Why?
#
#    It was built as a way to learn how GTK works. The fact that it also works
#    as an OK client is merely coincidental.
#
# 2. Install guide
#
#    The program is a self-contained Python script. It depends on `requests`,
#    `GTK` and `html2text`.
#
# 3. User manual
#
# 3.1. Keyboard shortcuts
#
#    In order to make it easier to use, the program has some keyboard
#    shortcuts. These shortcuts are common in other software as well, so it
#    should be easy to get accustomed.
#
#    - [CTRL-W] Closes the current tab
#    - [CTRL-R] Refreshes the current tab
#
################################################################################

################################################################################
# TODO List and planned features
################################################################################
#
# - Authentication with Pass
# - Posting replies to threads
# - Implement "New Thread"
# - Catalog search
# - Config file
#
################################################################################

import requests
from collections import namedtuple
import html, html2text
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
import threading
import time

# GUI Stuff
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GdkPixbuf

################################################################################
# In-memory Cache
################################################################################
#
# This is a simple in-memory TTL cache that stores Python objects. Objects that
# expire are routinely garbage collected.
#
################################################################################

__cache_data = {}


def cache_or_func(key, func, ttl):
    """
    Fetch the result from the cache, or fall back to a callable

    Parameters
    ----------
    key : str
        The cache key that uniquely represents the cached resource
    func
        Callable that calculates and returns the result to be cached
    ttl : int
        Time-to-live. How long a value should be cached for, in seconds.

    Returns
    -------
    The value, either retrieved from the cache or the result of calling func
    """
    t = time.monotonic()

    if key in __cache_data:
        value, expire_time = __cache_data[key]

        if expire_time > t:
            return value

    value = func()
    __cache_data[key] = value, t + ttl
    return value


def cache_gc():
    """Clean up the expired keys from the cache"""
    t = time.monotonic()

    for key in list(__cache_data.keys()):
        _, expire_time = __cache_data[key]

        if expire_time < t:
            del __cache_data[key]
    return True


GLib.timeout_add_seconds(10, cache_gc)


################################################################################
# Thread pool
################################################################################
#
# ThreadWidget provides asynchronously populated widgets that can load content
# or perform computation in a background thread pool.
#
################################################################################

thread_pool = ThreadPoolExecutor(max_workers=4)


class ThreadWidget(Gtk.Frame):
    def __init__(self):
        super().__init__()

    def __clear(self):
        for ch in self.get_children():
            self.remove(ch)

    def __glib_idle(self, future):
        GLib.idle_add(self.__update_ui, future)

    def __update_ui(self, future):
        self.__clear()
        self.build_ui()
        self.display(future.result())
        self.show_all()

    def __spinner(self):
        self.__clear()
        spin = Gtk.Spinner()
        spin.start()
        self.add(spin)
        self.show_all()

    def reload(self):
        self.__spinner()
        future = thread_pool.submit(self.load)
        future.add_done_callback(self.__glib_idle)

    def build_ui(self):
        pass

    def display(self, data):
        pass

    def load(self):
        pass


class CatalogThread:
    def __init__(self, data, board):
        self.data = data
        self.board = board

    @property
    def status(self):
        t = "<i>"
        t += str(self.data.get("replies"))
        t += " replies, "
        t += str(self.data.get("images"))
        t += " images</i>"
        return t

    @property
    def title(self):
        sub = self.data.get("sub", "")
        return html.unescape(sub)

    @property
    def comment(self):
        data = self.data.get("com", "")
        return html2text.html2text(data)

    @property
    def no(self):
        return self.data.get("no")

    @property
    def thumbnail(self):
        if "tim" not in self.data:
            return
        base = chan.I
        tim = self.data.get("tim")
        ext = self.data.get("ext")
        return f"{base}/{self.board}/{tim}s.jpg"


class Post:
    def __init__(self, data, board):
        self.data = data
        self.board = board

    @property
    def name(self):
        name = self.data.get("name")
        return name

    @property
    def no(self):
        return self.data.get("no")

    @property
    def body(self):
        data = self.data.get("com", "")
        return html2text.html2text(data)

    @property
    def date(self):
        return self.data.get("now")

    @property
    def thumbnail(self):
        if "tim" not in self.data:
            return
        base = chan.I
        tim = self.data.get("tim")
        ext = self.data.get("ext")
        return f"{base}/{self.board}/{tim}s.jpg"


################################################################################
# API Client
################################################################################
#
# Client to interact with the API.
#
################################################################################


class Chan:
    # URL constants
    A = "https://a.4cdn.org"
    I = "https://i.4cdn.org"

    def __init__(self):
        self.sess = requests.Session()
        self.sess.headers["User-Agent"] = "Python/ChanViewer v0.0"

    def get_cached(self, url, ttl):
        def inner():
            req = self.sess.get(url)
            return req.json()

        return cache_or_func(f"url_{url}", inner, ttl)

    @property
    def boards(self):
        url = f"{self.A}/boards.json"
        boards = self.get_cached(url, 60 * 15)
        return boards["boards"]

    def catalog(self, board):
        url = f"{self.A}/{board}/catalog.json"
        pages = self.get_cached(url, 60 * 2)
        for page in pages:
            for thread in page["threads"]:
                thread = CatalogThread(thread, board)
                yield thread

    def thread(self, board, thread):
        url = f"{self.A}/{board}/thread/{thread}.json"
        thread = self.get_cached(url, 60)
        for post in thread["posts"]:
            yield Post(post, board)


################################################################################
# Thumbnail image
################################################################################
#
# Displays a small image inline. Loads the image in a background task and caches
# it since images are not dynamic resources.
#
################################################################################


class ThumbnailImage(ThreadWidget):
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.reload()

    def display(self, pixbuf):
        img = Gtk.Image.new()
        img.set_from_pixbuf(pixbuf)
        self.add(img)
        set_margin(self, 5)

    def load(self):
        loader = GdkPixbuf.PixbufLoader()
        loader.write(self.image_content)
        loader.close()
        return loader.get_pixbuf()

    @property
    def image_content(self):
        def inner():
            return requests.get(self.url).content

        return cache_or_func(f"url_{self.url}", inner, 60 * 15)


class PostWidget(Gtk.Frame):
    def __init__(self, post):
        super().__init__()
        self.post = post
        self.build_ui()

    def build_ui(self):
        name = Gtk.Label.new()
        name.set_markup(f"<b>{self.post.name}</b>")

        date = Gtk.Label.new(self.post.date)

        no = Gtk.Label.new(str(self.post.no))

        body = Gtk.Label.new()
        body.set_line_wrap(True)
        body.set_text(self.post.body)

        hb = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 5)
        hb.add(name)
        hb.add(date)
        hb.add(no)

        vb = Gtk.Box.new(Gtk.Orientation.VERTICAL, 7)
        vb.add(hb)

        hb = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 0)
        if self.post.thumbnail:
            th = ThumbnailImage(self.post.thumbnail)
            hb.add(th)

        hb.pack_start(body, False, True, 0)
        vb.add(hb)

        set_margin(self, 10)
        set_margin(vb, 5)

        self.add(vb)


class ThreadPage(ThreadWidget):
    def __init__(self, board, no):
        super().__init__()
        self.board = board
        self.no = no
        self.reload()

    def build_ui(self):
        self.posts = Gtk.Box.new(Gtk.Orientation.VERTICAL, 5)
        scr = Gtk.ScrolledWindow.new()
        scr.add(self.posts)
        self.add(scr)

    def display(self, posts):
        for post in posts:
            self.posts.add(PostWidget(post))

    def load(self):
        return list(chan.thread(self.board, self.no))


class NewThread(Gtk.Window):
    def __init__(self, board):
        super().__init__(title=f"/{board}/ New thread")

        self.set_resizable(False)
        self.board = board

        self.widgets()

    def widgets(self):
        grid = Gtk.Grid()
        self.add(grid)

        name_label = Gtk.Label.new("Name")
        name_box = Gtk.Entry.new()

        subject_label = Gtk.Label.new("Subject")
        subject_box = Gtk.Entry.new()

        comment_label = Gtk.Label.new("Comment")
        comment_view = Gtk.TextView.new()
        comment_box = Gtk.ScrolledWindow.new()
        comment_box.add(comment_view)

        options_label = Gtk.Label.new("Options")
        options_box = Gtk.Entry.new()

        submit_button = Gtk.Button.new_with_label("Post")

        grid.attach(name_label, 0, 0, 1, 1)
        grid.attach_next_to(name_box, name_label, Gtk.PositionType.RIGHT, 30, 1)

        grid.attach_next_to(
            subject_label, name_label, Gtk.PositionType.BOTTOM, 1, 1
        )

        grid.attach_next_to(
            subject_box, subject_label, Gtk.PositionType.RIGHT, 30, 1
        )

        grid.attach_next_to(
            comment_label, subject_label, Gtk.PositionType.BOTTOM, 1, 20
        )

        grid.attach_next_to(
            comment_box, comment_label, Gtk.PositionType.RIGHT, 30, 20
        )

        grid.attach_next_to(
            options_label, comment_label, Gtk.PositionType.BOTTOM, 1, 1
        )

        grid.attach_next_to(
            options_box, options_label, Gtk.PositionType.RIGHT, 30, 1
        )

        grid.attach_next_to(
            submit_button, options_label, Gtk.PositionType.BOTTOM, 31, 1
        )

        grid.set_row_spacing(10)
        grid.set_column_spacing(10)

        set_margin(grid, 10)


#############
# GUI Helpers
#############


@contextmanager
def hbox(spacing=0):
    yield Gtk.Box.new(Gtk.Orientation.HORIZONTAL, spacing)


@contextmanager
def vbox(spacing=0):
    yield Gtk.Box.new(Gtk.Orientation.VERTICAL, spacing)


def set_margin(widget, amount):
    """
    Set all margins of a widget to a given value

    Parameters
    ----------
    widget : Gtk.Widget
        The target widget
    amount : int
        The amount of margin to add
    """
    widget.set_margin_top(amount)
    widget.set_margin_bottom(amount)
    widget.set_margin_start(amount)
    widget.set_margin_end(amount)


def thread_widget(thread, board):
    fr = Gtk.Frame.new(thread.title)

    with vbox() as vb:
        with hbox() as hb:
            if thread.thumbnail:
                th = ThumbnailImage(thread.thumbnail)
                hb.add(th)

            label = Gtk.Label.new()
            label.set_line_wrap(True)
            label.set_text(thread.comment[:250])
            hb.add(label)

        vb.pack_start(hb, True, True, 1)

        with hbox() as hb:
            label = Gtk.Label.new()
            label.set_markup(thread.status)

            hb.pack_start(label, True, True, 1)

            def view(_):
                tw = ThreadPage(board, thread.no)
                title = thread.title or "<Untitled>"
                win.create_tab(tw, f"{title} - /{board}/")

            btn = Gtk.Button.new_with_label("View thread")
            btn.connect("clicked", view)
            hb.pack_end(btn, False, False, 1)
            vb.pack_end(hb, False, False, 1)
        fr.add(vb)
    set_margin(vb, 10)
    set_margin(fr, 10)

    return fr


class Catalog(ThreadWidget):
    def __init__(self, board):
        super().__init__()
        self.board = board
        self.reload()

    def build_ui(self):
        with vbox(3) as page:
            with hbox(5) as top:
                search = Gtk.SearchEntry()
                top.pack_start(search, True, True, 0)
                new = Gtk.Button.new_with_label("New thread")
                new.connect("clicked", self.new_thread)
                top.pack_end(new, False, False, 5)
                page.pack_start(top, False, False, 0)
            page.add(Gtk.Separator.new(Gtk.Orientation.HORIZONTAL))

            scr = Gtk.ScrolledWindow()
            self.threads = Gtk.Box.new(Gtk.Orientation.VERTICAL, 3)
            scr.add(self.threads)
            page.pack_end(scr, True, True, 1)

            set_margin(page, 10)

            self.add(page)

    def display(self, threads):
        for thread in threads:
            widget = thread_widget(thread, self.board)
            self.threads.add(widget)

    def load(self):
        return list(chan.catalog(self.board))

    def new_thread(self, _):
        nt = NewThread(self.board)
        nt.show_all()


####################
# Board picker stuff
####################


def board_entry(board):
    name = board["board"]
    name = f"/{name}/"

    fr = Gtk.Frame.new(name)
    box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 10)

    box.add(Gtk.Label.new(board["title"]))

    desc = Gtk.Label.new()
    desc.set_text(html.unescape(board["meta_description"]))
    desc.set_line_wrap(True)
    box.pack_start(desc, True, True, 1)

    def open_tab(x):
        catalog = Catalog(board["board"])
        win.create_tab(catalog, name + " Catalog")

    btn = Gtk.Button.new_with_label("Open")
    btn.connect("clicked", open_tab)
    box.add(btn)

    set_margin(box, 10)

    fr.add(box)

    fr.set_margin_start(15)
    fr.set_margin_end(15)

    return fr


class Boards(ThreadWidget):
    def __init__(self):
        super().__init__()
        self.reload()

    def build_ui(self):
        self.box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 15)
        swin = Gtk.ScrolledWindow()
        swin.add(self.box)
        self.add(swin)

    def display(self, boards):
        for board in boards:
            self.box.add(board_entry(board))
            self.box.add(Gtk.Separator.new(Gtk.Orientation.HORIZONTAL))

    def load(self):
        return list(chan.boards)


class ChanViewer(Gtk.Window):
    def __init__(self):
        super().__init__(title="ChanViewer")
        self.connect("key-press-event", self.key_press)

        self.notebook = Gtk.Notebook()
        self.notebook.connect("page-added", self.tab_number_changed)
        self.notebook.connect("page-removed", self.tab_number_changed)
        self.add(self.notebook)

        self.create_tab(Boards(), "Boards")

    def create_tab(self, widget, title):
        with hbox() as hb:
            label = Gtk.Label.new(title)
            hb.pack_start(label, True, True, 5)

            def close_action(_):
                page = self.notebook.page_num(widget)
                self.notebook.remove_page(page)

            close = Gtk.ToolButton.new(Gtk.Label.new("x"))
            close.connect("clicked", close_action)
            hb.pack_end(close, False, False, 0)
            hb.show_all()

        page = self.notebook.append_page(widget, hb)
        self.notebook.set_tab_reorderable(widget, True)

        self.notebook.show_all()
        self.notebook.set_current_page(page)

    def tab_number_changed(self, *args):
        n = self.notebook.get_n_pages()

        if n == 0:
            Gtk.main_quit()

    def key_press(self, _, event):
        key = event.keyval
        key = Gdk.keyval_name(key)
        state = event.state
        ctrl = state & Gdk.ModifierType.CONTROL_MASK

        if ctrl and key == "w":
            page = self.notebook.get_current_page()
            self.notebook.remove_page(page)
        elif ctrl and key == "r":
            page = self.notebook.get_current_page()
            widget = self.notebook.get_nth_page(page)
            widget.reload()


chan = Chan()

win = ChanViewer()
win.connect("destroy", Gtk.main_quit)
win.show_all()

win.create_tab(Catalog("g"), "/g/ Catalog")

Gtk.main()

thread_pool.shutdown()
