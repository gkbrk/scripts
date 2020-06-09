#!/usr/bin/env python3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import urllib.request

ZONE = sys.argv[1]
ACCESS = sys.argv[2]
PATH = Path(sys.argv[3])

BASE = f"https://storage.bunnycdn.com/{ZONE}/"
AUTH = {"AccessKey": ACCESS}


def upload(path):
    if not path.is_file():
        return

    rel = str(path.relative_to(PATH))
    print(f"Uploading {rel}...")

    url = BASE + rel
    data = path.read_bytes()
    req = urllib.request.Request(url, data=data, headers=AUTH, method="PUT")
    urllib.request.urlopen(req)


with ThreadPoolExecutor(max_workers=4) as ex:
    ex.map(upload, PATH.rglob("*"))
