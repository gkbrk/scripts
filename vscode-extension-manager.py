#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import urllib.request
import json
import argparse
from pathlib import Path
import shutil
import tempfile
from typing import Any
from typing import Dict
from typing import Iterable
from typing import Union
from typing import Tuple
from typing import Callable
import hashlib
import subprocess
import time
import os

# Printing

orig_print = print


def print(s: str) -> None:
    replace_line(s)


def printn(s: str) -> None:
    replace_line(s)
    orig_print()


def replace_line(line: str) -> None:
    orig_print("\x1B[2K\r", end="", flush=True)
    orig_print(line, end="", flush=True)


# File-system cache


def cache_dir() -> Path:
    """Returns the path to the cache directory"""
    cache = None

    # Check the XDG cache
    cache = cache or os.environ.get("XDG_CACHE_HOME")

    # If it's not defined, just use ~/.cache
    if not cache:
        cache = str(Path.home() / ".cache")
    p = Path(cache) / "code-extension-manager"
    p.mkdir(parents=True, exist_ok=True)
    return p


def cache_path(key: str) -> Path:
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return cache_dir() / h


def cache_clean_old():
    """Cleans the cache of old files"""
    print("Cleaning old cached files...")
    for path in cache_dir().iterdir():
        if path.is_dir():
            shutil.rmtree(path)
        if path.is_file():
            # Get the age of the file
            age = time.time() - path.stat().st_mtime
            DAY = 60 * 60 * 24
            if age > DAY * 3:
                path.unlink()
                print(f"Cached file `{path}` is too old. Deleting...")


def cache_or(key: str, fn: Callable[[], bytes]) -> bytes:
    """Returns the data from the cache or calls the function"""
    path = cache_path(key)
    try:
        return path.read_bytes()
    except FileNotFoundError:
        data = fn()
        path.write_bytes(data)
        return data


# Utility functions

UA = "Mozilla/5.0 (X11; Linux x86_64; rv:108.0) Gecko/20100101 Firefox/108.0"

default_headers = {
    "User-Agent": UA,
}


def http_get(url: str) -> bytes:
    """Returns the data from the URL"""

    def inner():
        req = urllib.request.Request(url)

        for key, value in default_headers.items():
            req.add_header(key, value)

        with urllib.request.urlopen(req) as response:
            return response.read()

    return cache_or(f"HTTP_GET_{url}", inner)


def sha256sum(path: Path) -> str:
    """Returns the sha256sum of the file"""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(4096)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def editor_version() -> list[int]:
    cmd = [
        "code",
        "--version",
    ]

    res = subprocess.run(cmd, capture_output=True)
    output = res.stdout.decode("utf-8")

    version = output.split("\n")[0].split(" ")[-1].split(".")
    return [int(x) for x in version]


def fits_editor_version(editor: list[int], semver: str) -> bool:
    """Check if the editor version fits the semver.

    The semver string can start with a caret (^) to indicate a minimum version.
    """

    if semver == "*":
        return True

    if semver.startswith("^"):
        parts = semver[1:].split("-")[0].split(".")
        min_version = [int(x) for x in parts]
        return editor >= min_version

    printn(f"{editor} {semver}")
    raise ValueError("Cannot understand semver string")


def extensions_file() -> Path:
    """Returns the path to the extensions file"""
    p = Path(ARGS.directory).expanduser() / "extensions.txt"
    return p.resolve()


def parse_extensions_file() -> Iterable[Tuple[str, str]]:
    """Parses the extensions file and returns the list of extensions"""
    for line in extensions_file().read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        method, data = line.split(" ", 1)
        yield method, data


def extensions_dir() -> Path:
    """Returns the path to the extensions directory"""
    p = Path(ARGS.directory).expanduser() / "extensions"
    return p.resolve()


def ensure_extensions_dir():
    extensions_dir().mkdir(parents=True, exist_ok=True)
    extensions_file().touch()


def download_file(url: str) -> Path:
    total = 0
    print(f"Downloading {url}...")

    path = cache_path(f"HTTP_GET_{url}")

    if path.exists():
        print("Already downloaded")
        return path

    req = urllib.request.Request(url)
    for key, value in default_headers.items():
        req.add_header(key, value)

    with urllib.request.urlopen(req) as response:
        try:
            length = int(response.getheader("Content-Length"))
        except (TypeError, ValueError):
            length = None
        with path.open("wb") as f:
            while True:
                chunk = response.read(4096)
                if not chunk:
                    break
                total += len(chunk)
                f.write(chunk)

                if length:
                    pct = f"{total / length * 100:.2f}%"
                    downloaded = f"{total / 1000 / 1000:.2f} MB"
                    all = f"{length / 1000 / 1000:.2f} MB"

                    print(f"Downloading {pct} ({downloaded} / {all})")
                else:
                    print(f"Downloading {total / 1000:.2f} KB")
    orig_print()
    return path


def install_vsix(path: Path):
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        vsix = tmp / "extension.vsix"
        shutil.copy(path, vsix)

        # Now let's extract the vsix
        subprocess.run(
            ["unzip", "-q", "-d", tmp, tmp / "extension.vsix"],
            check=True,
            cwd=tmp,
        )

        # Now let's copy the extension to the extensions directory
        hash = sha256sum(tmp / "extension.vsix")
        extension_dir = extensions_dir() / hash
        extension_dir.mkdir(parents=True, exist_ok=True)
        shutil.copytree(tmp / "extension", extension_dir, dirs_exist_ok=True)


# Providers


class ExtensionProvider:
    def name(self):
        raise NotImplementedError()

    def install(self, data: str):
        raise NotImplementedError()


class OpenVSXProvider(ExtensionProvider):
    def name(self):
        return "Open VSX Registry"

    def install(self, data: str):
        url = OpenVSXProvider.find_download_url(data)
        path = download_file(url)
        install_vsix(path)

    @staticmethod
    def find_download_url(name: str) -> str:
        """Finds the download URL for the given extension"""
        publisher, extension = name.split(".", 1)
        url = f"https://open-vsx.org/api/{publisher}/{extension}/latest"
        data = http_get(url)
        data = json.loads(data)
        return data["files"]["download"]


class VSCodeProvider(ExtensionProvider):
    def name(self):
        return "VSCode Marketplace"

    def install(self, data: str):
        url = VSCodeProvider.find_download_url(data)
        path = download_file(url)
        install_vsix(path)

    @staticmethod
    def find_download_url(name: str) -> str:
        """Finds the download URL for the given extension"""

        try:
            name, data = name.split(" ", 1)
            additional = json.loads(data)
        except Exception:
            name = name
            additional = {}

        fn = lambda: VSCodeProvider.vscode_query(name)
        data = cache_or(f"VSCode_{name}", fn)
        data = json.loads(data)

        # VSIX URL
        versions = data["results"][0]["extensions"][0]["versions"]
        version: Union[None, Dict[str, Any]] = None

        editor_ver = editor_version()

        def check_version(ver):
            manifest = VSCodeProvider.manifest_editor_version(ver)
            if not manifest:
                return False

            if fits_editor_version(editor_ver, manifest):
                return True

            return False

        for ver in versions:
            if check_version(ver):
                version = ver
                break

        if not version:
            raise Exception(f"Could not find version for {name}")

        for f in version["files"]:
            if f["assetType"] == "Microsoft.VisualStudio.Services.VSIXPackage":
                return f["source"]

        raise Exception("Could not find VSIX package")

    @staticmethod
    def manifest_editor_version(version: dict) -> str:
        for f in version["files"]:
            if f["assetType"] == "Microsoft.VisualStudio.Code.Manifest":
                manifest_url = f["source"]
                break
        else:
            raise Exception("Could not find manifest")

        manifest = http_get(manifest_url)
        manifest = json.loads(manifest)

        return manifest["engines"]["vscode"]

    @staticmethod
    def vscode_query(name: str) -> bytes:
        URL = "https://marketplace.visualstudio.com/_apis/public/gallery/extensionquery"
        body = json.dumps(
            {
                "assetTypes": None,
                "filters": [
                    {
                        "criteria": [{"filterType": 7, "value": name}],
                        "direction": 2,
                        "pageSize": 100,
                        "pageNumber": 1,
                        "sortBy": 0,
                        "sortOrder": 0,
                        "pagingToken": None,
                    }
                ],
                "flags": 2151,
            }
        )

        # Send the request
        req = urllib.request.Request(URL, data=body.encode("utf-8"))

        for key, value in default_headers.items():
            req.add_header(key, value)

        req.add_header(
            "Accept",
            "application/json;api-version=7.1-preview.1;excludeUrls=true",
        )
        req.add_header("Accept-Language", "en-US,en;q=0.5")
        req.add_header("Content-Type", "application/json")
        req.add_header("X-VSS-ReauthenticationAction", "Suppress")

        # Get the response
        with urllib.request.urlopen(req) as response:
            return response.read()


PROVIDERS = {
    "openvsx": OpenVSXProvider(),
    "vscode": VSCodeProvider(),
}

# Actions


def action_restore():
    printn("Restoring extensions...")
    extensions_dir().mkdir(parents=True, exist_ok=True)
    printn("Removing installed extensions...")
    shutil.rmtree(extensions_dir())
    extensions_dir().mkdir(parents=True, exist_ok=True)
    cache_clean_old()

    for method, data in parse_extensions_file():
        if method in PROVIDERS:
            prov = PROVIDERS[method]
            printn(f"Installing {data} from {prov.name()}...")
            prov.install(data)
        else:
            printn(f"Unknown method `{method}`, skipping {data}")


def action_providers():
    print("Available providers")
    print("-------------------")
    for name, prov in PROVIDERS.items():
        print(f"{name}: {prov.name()}")


def action_list():
    print("List of extensions")
    print("------------------")
    for method, data in parse_extensions_file():
        print(f"{method: <10} {data}")


# Parse command line arguments
parser = argparse.ArgumentParser()
parser.description = "VS Code extensions manager"
parser.add_argument(
    "--directory", help="VS Code directory", default="~/.vscode-oss"
)

# Subparsers
subparsers = parser.add_subparsers(
    help="The sub-command to execute", dest="action", required=True
)

# Restore sub-command
restore_parser = subparsers.add_parser("restore", help="Restore extensions")
restore_parser.set_defaults(func=action_restore)

# Providers sub-command
providers_parser = subparsers.add_parser(
    "providers", help="List available providers"
)
providers_parser.set_defaults(func=action_providers)

# List sub-command
list_parser = subparsers.add_parser("list", help="List installed extensions")
list_parser.set_defaults(func=action_list)

# Parse arguments
ARGS = parser.parse_args()

# Execute action
ARGS.func()
printn("")
