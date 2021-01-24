#!/usr/bin/env python
import json
import subprocess
import time
import fcntl
from pathlib import Path
from collections import defaultdict

DB_PATH = Path("db.json")
DB_PATH_TMP = Path("db.json.tmp")

try:
    db = json.loads(DB_PATH.read_text())
except:
    db = {}
    db["Tasks"] = {}
    db["CreatedAt"] = int(time.time())

db["LastAccess"] = int(time.time())

valid = []

for path in Path("tasks/").iterdir():
    if str(path) not in db["Tasks"]:
        db["Tasks"][str(path)] = {}
    valid.append(str(path))
    task = db["Tasks"][str(path)]
    for metaline in subprocess.run([path, "metadata"], capture_output=True).stdout.decode("utf-8").split("\n"):
        metaline = metaline.strip()

        if not metaline:
            continue
        
        name, val = metaline.split(" ", 1)
        task[name] = val

    lastExecuted = task.get("LastExecuted", 0)
    interval = int(task.get("interval", "300"))

    if time.time() > lastExecuted + interval:
        task["LastExecuted"] = int(time.time())

        res = subprocess.run([path, "get-result"], capture_output=True)

        lastOutput = task.get("LastOutput", "")

        if lastOutput != res.stdout.decode("utf-8"):
            subprocess.run([path, "change-detected"], capture_output=True, input=res.stdout)

        task["LastOutput"] = res.stdout.decode("utf-8")

for task in list(db["Tasks"].keys()):
    if task not in valid:
        del db["Tasks"][task]

DB_PATH_TMP.write_text(json.dumps(db))
DB_PATH_TMP.rename(DB_PATH)
