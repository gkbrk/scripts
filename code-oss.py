#!/usr/bin/env python3
import subprocess
import sys
import os
import weakref
import json
import datetime
from pathlib import Path

if os.fork() != 0:
    os._exit(0)

os.setsid()

if os.fork() != 0:
    os._exit(0)


class TempPath:
    def __init__(self):
        prefix = "code-oss"
        rand = os.urandom(16).hex()
        today = datetime.date.today()
        yyyymmdd = today.strftime("%Y%m%d")
        p = f"/tmp/{prefix}-{yyyymmdd}-{rand}"
        self.__path = Path(p)
        self.__path.mkdir()

        self.__f = weakref.finalize(self, subprocess.run, ["rm", "-rf", p])

    def __enter__(self) -> Path:
        return self.__path

    def __exit__(self, _exc_type, _exc_value, _tb):
        self.__f()

    def __fspath__(self) -> str:
        return str(self.__path)

    def __str__(self) -> str:
        return str(self.__path)

    def __truediv__(self, other) -> Path:
        return self.__path / other


EXECUTABLE = "code"
CODE_USER_DATA_DIR = TempPath()
CODE_EXTENSIONS_DIR = TempPath()

PROFILE = Path.home() / "leo-code-oss"

for p in (PROFILE / "userdata").iterdir():
    subprocess.run(["cp", "-R", p.resolve(), CODE_USER_DATA_DIR], check=False)

extension_ids = set()

for p in (PROFILE / "extensions").iterdir():
    target = CODE_EXTENSIONS_DIR / os.urandom(16).hex()
    target.mkdir()

    t = TempPath()

    cmd = ["unzip", "-q", "-d", t, p.resolve()]
    subprocess.run(cmd, check=False, cwd=t)

    package_json = json.loads(
        (t / "extension" / "package.json").read_text(encoding="utf-8")
    )
    extension_ids.add(package_json["publisher"] + "." + package_json["name"])

    for x in (t / "extension").iterdir():
        cmd = ["cp", "-R", x, target.resolve()]
        subprocess.run(cmd, check=False)

cmd = [
    EXECUTABLE,
    "--wait",
    "--user-data-dir",
    CODE_USER_DATA_DIR,
    "--extensions-dir",
    CODE_EXTENSIONS_DIR,
    "--locale",
    "en-US",
]

for ext in extension_ids:
    cmd.append("--enable-proposed-api")
    cmd.append(ext)

cmd += sys.argv[1:]

subprocess.run(cmd, check=False)

subprocess.run(["pkill", "-9", "--full", str(CODE_USER_DATA_DIR)], check=False)
