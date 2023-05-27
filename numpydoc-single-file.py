#!/usr/bin/env python3

"""Create numpydoc exports from a single Python file."""

import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.argv.pop(0)
source_file = Path(sys.argv.pop(0))
target = Path(sys.argv.pop(0))

kv = {}
while sys.argv:
    n = sys.argv.pop(0)
    v = sys.argv.pop(0)
    kv[n] = v

target.parent.mkdir(parents=True, exist_ok=True)

with tempfile.TemporaryDirectory(prefix="numpydoc-") as tmp:
    tmp = Path(tmp)

    (tmp / "source" / f"{kv['moduleName']}.py").parent.mkdir(
        parents=True, exist_ok=True
    )
    (tmp / "src").mkdir(parents=True, exist_ok=True)
    (tmp / "dest").mkdir(parents=True, exist_ok=True)

    (tmp / "source" / f"{kv['moduleName']}.py").write_text(
        source_file.read_text()
    )

    conf = f"""
project = "{source_file.name}"
copyright = "{time.strftime("%Y")}"
html_theme = "pydata_sphinx_theme"

import sys
sys.path.append("{tmp / "source"}")

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.doctest",
    "numpydoc",
]

numpydoc_show_class_members = False

html_sidebars = {{
  "**": []
}}

html_theme_options = {{
  "show_toc_level": 2
}}

doctest_path = sys.path

doctest_global_setup = '''
import sys
sys.path.append("{tmp / "source"}")
import {kv["moduleName"]}
from {kv["moduleName"]} import *
'''

"""
    (tmp / "src" / "conf.py").write_text(conf)

    index = "\n".join(
        [
            x[4:]
            for x in filter(
                lambda x: x.startswith("###"),
                source_file.read_text().split("\n"),
            )
        ]
    )
    index += "\n"
    (tmp / "src" / "index.rst").write_text(index)

    for _ in range(2):
        subprocess.run(["sphinx-build", "-b", "html", "src", "dest"], cwd=tmp)

    # subprocess.run(["/bin/sh"], cwd=tmp)
    subprocess.run(["sphinx-build", "-M", "doctest", "src", "dest"], cwd=tmp)

    serv = subprocess.Popen(
        ["python3", "-m", "http.server", "--directory", tmp / "dest", "14383"]
    )

    # Save the output of as a single file
    subprocess.run(
        "podman run --net=host docker.io/capsulecode/singlefile 'http://127.0.0.1:14383/' > output.html",
        shell=True,
        cwd=tmp,
    )
    serv.terminate()

    target.write_text((tmp / "output.html").read_text())
