#!/usr/bin/env python3

import subprocess
import os
from concurrent.futures import ThreadPoolExecutor
import time
from contextlib import contextmanager

# GUI Stuff
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib


def label(text):
    return Gtk.Label.new(text)


def sudo_dialog(cmd):
    """Accept superuser password from a GUI dialog.

    Create a popup dialog and ask for the sudo password.

    Parameters
    ----------
    cmd : str
        The command to display to the user.

    Returns
    -------
    str
        The password.
    """
    dialog = Gtk.Dialog(title="Sudo access")
    dialog.set_default_size(150, 100)
    dialog.set_resizable(False)

    entry = Gtk.Entry.new()
    entry.set_visibility(False)
    entry.connect("activate", lambda x: dialog.response(0))

    box = dialog.get_content_area()
    lbl = Gtk.Label.new(
        "Arch package remover needs superuser access to run the following command"
    )
    box.add(lbl)
    box.add(Gtk.Label.new(cmd))
    box.add(entry)
    box.show_all()

    dialog.run()
    text = entry.get_text()
    dialog.destroy()

    return text


def run_with_sudo(command):
    """Run a command as root.

    Parameters
    ----------
    command : list of str
        The command to execute

    Returns
    -------
    None
    """
    password = sudo_dialog(" ".join(command))

    # sudo -k invalidates the "sudo cache". We do this in order to make sudo ask
    # for the password every time.
    subprocess.run(["sudo", "-k"])

    # The -S flag to `sudo` allows us to pass the password through stdin.
    subprocess.run(["sudo", "-S", *command], input=password.encode("utf-8"))


def str_between(s, left, right):
    """Extract the value between two substrings.

    Parameters
    ----------
    s : str
        The string to search in.
    left : str
    right : str

    Returns
    -------
    str
        The value between `left` and `right`.
    """
    s = s.split(left, 2)[1]
    s = s.split(right, 2)[0]

    return s


class Pacman:
    """Python interface to Pacman."""

    def __init__(self):
        pass

    @property
    def version(self):
        """The version of the Pacman package manager.

        Try to execute `pacman -V` and extract the version field.

        Returns
        -------
        str
            The version of Pacman that is installed on this system.

        """
        proc = subprocess.run(["pacman", "-V"], capture_output=True)
        outp = proc.stdout.decode("ascii")
        return str_between(outp, "Pacman v", " ")

    @property
    def explicit_list(self):
        proc = subprocess.run(["pacman", "-Qe"], capture_output=True)

        for line in proc.stdout.decode("ascii").split("\n"):
            if not line:
                continue
            pkg, ver = line.split(" ", 2)
            yield pkg

    def remove(self, pkgname):
        if pkgname not in list(self.explicit_list):
            log("Package", pkgname, "is not in the explicit list")
            return

        log("Attemping to remove", pkgname)
        run_with_sudo(["pacman", "-Rs", "--noconfirm", pkgname])

        if pkgname in list(self.explicit_list):
            log(f"Failed to remove {pkgname}. It's still installed.")
        else:
            log(f"Successfully removed package {pkgname}")

    def mark_non_explicit(self, pkgname):
        run_with_sudo(["pacman", "-D", "--asdeps", pkgname])

    def info(self, pkgname):
        proc = subprocess.run(["pacman", "-Qi", pkgname], capture_output=True)
        for line in proc.stdout.decode("utf-8").split("\n"):
            if line:
                yield line

    def dry_run_remove(self, pkgname):
        proc = subprocess.run(["pacman", "-Rsp", pkgname], capture_output=True)
        for line in proc.stdout.decode("utf-8").split("\n"):
            if line:
                yield line


logbuffer = []


def log(*a):
    a = [str(x) for x in a]
    text = " ".join(a)
    t = time.strftime("%H:%M:%S")
    text = f"[{t}] {text}"

    print(text)

    try:
        while logbuffer:
            dbgWidget.log(logbuffer[0])
            logbuffer.pop(0)
    except:
        pass

    try:
        dbgWidget.log(text)
    except:
        logbuffer.append(text)


@contextmanager
def hbox(spacing=0):
    yield Gtk.Box.new(Gtk.Orientation.HORIZONTAL, spacing)


@contextmanager
def vbox(spacing=0):
    yield Gtk.Box.new(Gtk.Orientation.VERTICAL, spacing)


class DebugLogWidget(Gtk.Bin):
    """Debug log widget"""

    def __init__(self):
        super().__init__()
        self.build_ui()

    def build_ui(self):
        self.scroll = Gtk.ScrolledWindow.new()
        self.box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 5)
        self.scroll.add(self.box)
        self.add(self.scroll)

    def log(self, text):
        """Append a line to the debug log.

        Appends a new line to the debug log widget and scrolls it to the bottom.

        Parameters
        ----------
        text : str
            The string to log. Should be a single line.

        Returns
        -------
        None

        """
        with hbox() as h:
            h.add(Gtk.Label.new(text))
            self.box.add(h)
        adj = self.scroll.get_vadjustment()
        adj.set_page_size(0)
        adj.set_value(adj.get_upper())
        self.show_all()


class PackageList(Gtk.Bin):
    def __init__(self):
        super().__init__()
        self.plist = []

    def lazy_reload(self):
        plist = list(pacman.explicit_list)

        if plist != self.plist:
            if self.plist:
                log("Package list changed, reloading...")
            self.plist = plist
            self.reload()

    def reload(self):
        self.foreach(self.remove)

        fr = Gtk.Frame.new("Package list")

        scr = Gtk.ScrolledWindow.new()
        scr.set_propagate_natural_width(True)

        grid = Gtk.Grid.new()

        for row, pkg in enumerate(self.plist):
            grid.attach(Gtk.Label.new(pkg), 0, row, 1, 1)

            btn = Gtk.Button.new()

            def make_handler(pkg):
                def inner(x):
                    globals()["pkgDetails"].load_package(pkg)

                return inner

            btn.connect("clicked", make_handler(pkg))
            btn.set_label("Details")

            grid.attach(btn, 1, row, 1, 1)

            btn = Gtk.Button.new()

            def make_handler(pkg):
                def inner(x):
                    pacman.remove(pkg)

                return inner

            btn.connect("clicked", make_handler(pkg))
            btn.set_label("Remove")

            grid.attach(btn, 2, row, 1, 1)

            btn = Gtk.Button.new()

            def make_handler(pkg):
                def inner(x):
                    pacman.mark_non_explicit(pkg)

                return inner

            btn.connect("clicked", make_handler(pkg))
            btn.set_label("Non-explicit")

            grid.attach(btn, 3, row, 1, 1)

        grid.set_column_spacing(15)
        grid.set_row_spacing(10)

        scr.add(grid)
        fr.add(scr)
        self.add(fr)
        self.show_all()


class PackageDetails(Gtk.Bin):
    def __init__(self):
        super().__init__()

    def load_package(self, pkgname):
        log(f"Loading details for '{pkgname}'")
        self.foreach(self.remove)

        scr = Gtk.ScrolledWindow.new()
        with vbox() as v:

            def add_line(line):
                with hbox() as h:
                    h.add(Gtk.Label.new(line))
                    v.add(h)

            for line in pacman.info(pkgname):
                add_line(line)

            add_line("")
            add_line("Removing this package will get rid of:")
            add_line("")
            for line in pacman.dry_run_remove(pkgname):
                add_line(f"- {line}")
            scr.add(v)
        self.add(scr)
        self.show_all()


class ArchPkgRemove(Gtk.Window):
    def __init__(self):
        super().__init__(title="Arch package remover")

        # Kill GTK when this window is closed
        self.connect("destroy", Gtk.main_quit)

        self.build_ui()

    def build_ui(self):
        pkgList.set_margin_top(20)
        pkgList.set_margin_bottom(20)

        with hbox() as h:
            h.pack_start(pkgList, False, True, 1)

            with vbox() as v:
                fr = Gtk.Frame.new("Package details")
                fr.add(pkgDetails)
                v.pack_start(fr, True, True, 1)

                fr = Gtk.Frame.new("Debug log")
                dbgWidget.scroll.set_min_content_height(200)
                dbgWidget.scroll.set_max_content_height(200)
                fr.add(dbgWidget)
                v.pack_end(fr, False, True, 1)

                h.pack_end(v, True, True, 1)

            self.add(h)


def reloadPkgList():
    try:
        globals()["pkgList"].lazy_reload()
    except:
        pass
    return True


GLib.timeout_add_seconds(1, reloadPkgList)


def main():
    globals()["pacman"] = Pacman()
    globals()["dbgWidget"] = DebugLogWidget()
    globals()["pkgDetails"] = PackageDetails()
    globals()["pkgList"] = PackageList()

    win = ArchPkgRemove()
    win.show_all()

    log(f"Found pacman version {pacman.version}")
    pkgList.lazy_reload()
    pkgDetails.load_package(next(pacman.explicit_list))
    Gtk.main()

    # Do not wait to clean up resources, exit should be instant
    os._exit(0)


if __name__ == "__main__":
    log("Script started, running main()")
    main()
