#!/usr/bin/env python3
# Copyright (C) 2020 Gokberk Yaltirakli
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE X
# CONSORTIUM BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from pathlib import Path
from collections import namedtuple
from itertools import cycle
import os, sys, argparse

# Self-contained, limited implementation of the Ninja build system

# As a disclaimer, this implementation is missing a lot of details.  But it is
# enough to build my projects, even ones with multiple compilers, file formats
# and different link steps.

# This can be used as an educational exercise, or as a way to build software
# that uses ninja build files if you do not have access to a better ninja
# implementation.

# You can find the manual at https://ninja-build.org/manual.html.  With all the
# license stuff and disclaimers out of the way, let's begin.

#-------------------------------------------------------------------------------

# Parse the supported command line arguments. We could ignore most of these, but
# they don't inflate the code too much so it's worth the extra flexibility.

parser = argparse.ArgumentParser()

# By default, ninja uses the build.ninja file. This can be overridden using the
# -f flag.
parser.add_argument("-f", "--file", default="build.ninja")

# Dry run pretends to run the commands without actually running them.
parser.add_argument("-n", "--dry-run", action="store_true")

# Verbose, makes the output noisy with commands that are being run.
parser.add_argument("-v", "--verbose", action="store_true")

# Targets that you want to build instead of the default ones.
parser.add_argument("targets", nargs="*")

args = parser.parse_args()

# ------------------------------------------------------------------------------

# Let's start by checking if the file exists.  If it does, we'll read it line by
# line into a list.

build_file = Path(args.file)

if not build_file.exists():
    # Uh-oh, nothing we can do here
    print("Build file not found")
    sys.exit(1)

# Read the build file. Strip trailing whitespace from the lines.

lines = []
with open(build_file) as bf:
    for line in bf:
        lines.append(line.rstrip())

# ------------------------------------------------------------------------------

# If everything went well, we are ready to parse the build file. First, let's
# make the structures that we will be filling during the parse.

# Contains the rules for building the statements
rules = {}

# Contains the build targets and their dependencies
Statement = namedtuple("Statement", "rule deps")
statements = {}

# The targets to build
targets = []

# The parser we're building will be made up of small functions that parse
# different sections of the build file. The parser will run each function in
# succession until we are out of lines to parse. This is where we will keep the
# functions.

parsers = []

# Check if a line is completely empty, then remove it.  This is the simplest
# function we can write, but it doesn't get too complicated.
def parse_whitespace(lines):
    assert lines[0].strip() == ""
    lines.pop(0)


parsers.append(parse_whitespace)


# Parse build statements. These are in the form `build TARGET: RULE DEPS`. They
# can actually contain more information, but this is a simplified
# implementation.
def parse_build(lines):
    action = lines[0].split(" ", 1)[0]
    assert action == "build"

    line = lines.pop(0)
    p1, p2 = line.split(":")
    target = p1.split(" ")[1]
    p2 = list(filter(None, p2.split(" ")))
    rule = p2[0]
    deps = p2[1:]
    stm = Statement(rule, deps)
    statements[target] = stm


parsers.append(parse_build)


# Parses the default command. The format is `default target1 target2...`. This
# command is used to set the default targets to build.
def parse_default(lines):
    parts = lines[0].split(" ")
    assert parts[0] == "default"

    # Filter out the empty strings and add the rest to targets.
    for target in filter(None, parts[1:]):
        targets.append(target)

    # Finally, consume the line we just read
    lines.pop(0)


parsers.append(parse_default)


def parse_rule(lines):
    rule, name = lines[0].split(" ", 1)
    assert rule == "rule"
    lines.pop(0)

    data = {}
    while True:
        l = lines[0]
        if l.startswith(" "):
            l = lines.pop(0)
            key, val = l.split("=", 1)
            key = key.strip()
            val = val.strip()
            data[key] = val
        else:
            break

    rules[name] = data


parsers.append(parse_rule)

# That's all the parsing code we're going to write.  Let's run them in a loop
# until all the input is consumed.

for parser in cycle(parsers):
    try:
        parser(lines)
    except:
        pass

    if not len(lines):
        break

# ------------------------------------------------------------------------------

# Everything is now (hopefully) parsed. The next step is to figure out what to
# build. And for that we need a list of targets.

# If there are no targets specified with the default command or with command
# line arguments, build everything. Otherwise, build the targets.

if not targets:
    for target in statements:
        targets.append(target)
if args.targets:
    targets = args.targets

# But the list of targets is not all we need to start building the code. The
# files might have multiple dependencies and go through different build
# steps. We need to go through the dependency graph, and order them in a way
# that we can build them sequentially without having missing dependencies.

# This is called a "Topological Sort", and you can read more about it on
# Wikipedia.

build_list = []  # Ordered list of how to build things

perm = set()  # Permanent marker
temp = set()  # Temporary marker
unmarked = set(targets)  # Unmarked nodes, i.e. build targets


def visit(n):
    if n in perm:
        return

    if n in temp:
        print("Cannot sort dependencies")
        sys.exit(1)

    temp.add(n)

    if n in statements:
        for dep in statements[n].deps:
            visit(dep)

    temp.remove(n)
    perm.add(n)
    build_list.append(n)


while unmarked or temp:
    n = unmarked.pop()
    visit(n)

# ------------------------------------------------------------------------------

# With the topological sort out of the way, we now know that if we just build
# things in order, everything will work out. So let's do that.

for target in build_list:
    # Check if  we know how to  build the target.  If we don't, it's  probably a
    # code file or generated by another command.
    if target not in statements:
        continue

    # Get the statement and the rule
    statement = statements[target]
    rule = rules[statement.rule]

    # Get the  command from the  rule, and do  a quick variable  substitution to
    # replace the input and output file names.
    cmd = rule["command"]
    cmd = cmd.replace("$in", " ".join(statement.deps))
    cmd = cmd.replace("$out", target)

    # If the verbose flag is passed, print the command that we are about to run
    if args.verbose:
        print(cmd)

    # If we are not in a dry run, execute the command
    if not args.dry_run:
        os.system(cmd)
