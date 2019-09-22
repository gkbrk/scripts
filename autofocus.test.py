#!/usr/bin/env python3
from testsimple import *
import subprocess
import tempfile
from tempfile import NamedTemporaryFile
import os


def run(args):
    return subprocess.run(args, shell=True, capture_output=True)


class AutofocusTest:
    def __init__(self, scenario=None):
        self.scenario = scenario

    def read_file(self):
        with open(self.temp) as tf:
            return tf.read()

    def run(self, command):
        res = run(f"./autofocus {self.temp} {command}")
        ok(res.returncode == 0)
        return res

    def __enter__(self):
        if self.scenario:
            diag(self.scenario)
        _, self.temp = tempfile.mkstemp()
        return self

    def __exit__(self, x, y, z):
        os.unlink(self.temp)


testTasks = ["Test task one", "Test task two", "Test task three"]

testFile = "\n".join(testTasks) + "\n"

with test("Running without target file should error"):
    result = run("./autofocus")
    ok(result.returncode != 0)

with AutofocusTest("Running with a target file should not error") as t:
    t.run("")

with test("Running the command on a target file should display the tasks"):
    with NamedTemporaryFile() as tf:
        tf.write(testFile.encode("utf-8"))
        tf.flush()

        result = run(f"./autofocus {tf.name}")
        ok(result.returncode == 0)

        for task in testTasks:
            ok(task in result.stdout.decode("utf-8"))

with AutofocusTest("The add command should append to the file") as t:
    for task in testTasks:
        t.run(f"add {task}")

    ok(t.read_file() == testFile)

with AutofocusTest("The strike command should strike the given item") as t:
    t.run("add Test task one")
    t.run("add Test task two")
    t.run("strike 1")

    ok(t.read_file() == "Test task one\n~Test task two~\n")

    t.run("strike 0")

    ok(t.read_file() == "~Test task one~\n~Test task two~\n")

with AutofocusTest("Using strike on an already striked item will reverse it") as t:
    t.run("add Test task one")
    ok(t.read_file() == "Test task one\n")
    t.run("strike 0")
    ok(t.read_file() == "~Test task one~\n")
    t.run("strike 0")
    ok(t.read_file() == "Test task one\n")

with AutofocusTest("The sink command shouldn't affect normal items") as t:
    t.run("add Test task one")
    t.run("add Test task two")

    ok(t.read_file() == "Test task one\nTest task two\n")
    t.run("sink")
    ok(t.read_file() == "Test task one\nTest task two\n")

done_testing()
