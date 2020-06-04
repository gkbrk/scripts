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
import os, sys, argparse, re

# Self-contained, limited implementation of the Ninja build system

# As a disclaimer, this implementation is missing a lot of details.  But it is
# enough to build my projects, even ones with multiple compilers, file formats
# and different link steps.

# This can be used as an educational exercise, or as a way to build software
# that uses ninja build files if you do not have access to a better ninja
# implementation.

# You can find the manual at https://ninja-build.org/manual.html.  With all the
# license stuff and disclaimers out of the way, let's begin.

# -------------------------------------------------------------------------------

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

# Read the build file, do minimal preprocessing

lines = []
with open(build_file) as bf:
    bf = iter(bf)
    for line in bf:
        # Strip traling whitespace from lines
        line = line.rstrip()

        # Ignore empty lines
        if not line:
            continue

        # Ignore comments
        if line.lstrip().startswith("#"):
            continue

        # Lines ending with $ are joined to the next line
        while line.endswith("$"):
            line = line[:-1] + next(bf).strip()

        lines.append(line)

# ------------------------------------------------------------------------------

# The Ninja build format is whitespace-sensitive.

Block = namedtuple("Block", "directive variables")


def indented(line):
    if not line:
        return False
    else:
        return line[0] in [" ", "\t"]


def get_variable(line):
    try:
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        return name, value
    except:
        return None


# Performs basic lexing


def get_blocks(lines):
    lines = list(lines)

    block = None

    for line in lines:
        var = get_variable(line)

        if var:
            name, value = var
            if indented(line):
                block.variables[name] = value
            else:
                yield Block(None, {name: value})
        else:
            if block:
                yield block
            block = Block(line, {})
    yield block


blocks = list(get_blocks(lines))

# ------------------------------------------------------------------------------
Rule = namedtuple("Rule", "name")
Build = namedtuple("Build", "target rule deps impl order")
Default = namedtuple("Default", "targets")


def replace_variables(line, bl=None):
    variables = {}

    for block in blocks:
        if block.directive is None:
            for key in block.variables:
                variables[key] = block.variables[key]

    if bl:
        for key in bl.variables:
            variables[key] = bl.variables[key]

    prev = None
    while prev != line:
        prev = line
        for var in re.findall("\$([A-Za-z0-9]+)", line):
            if var in variables:
                line = line.replace(f"${var}", variables[var])
    return line


def parse_directive(block):
    if not block.directive:
        return block

    directive = replace_variables(block.directive, block)
    command, arg = directive.split(" ", 1)

    directive = None

    if command == "build":
        target, deps = arg.split(":")
        deps = list(filter(None, deps.split(" ")))
        rule = deps[0]

        expl = []
        impl = []
        order = []

        bucket = expl
        for dep in deps[1:]:
            if dep == "|":
                bucket = impl
            elif dep == "||":
                bucket = order
            else:
                bucket.append(dep)

        directive = Build(target, rule, expl, impl, order)
    elif command == "rule":
        directive = Rule(arg)
    elif command == "default":
        targets = list(filter(None, arg.split(" ")))
        directive = Default(targets)
    return Block(directive, block.variables)


blocks = list(map(parse_directive, blocks))

# Some helper functions to search the blocks


def get_build(target):
    for block in blocks:
        if (
            isinstance(block.directive, Build)
            and block.directive.target == target
        ):
            return block


def get_rule(name):
    for block in blocks:
        if isinstance(block.directive, Rule) and block.directive.name == name:
            return block


# ------------------------------------------------------------------------------

# Everything is now (hopefully) parsed. The next step is to figure out what to
# build. And for that we need a list of targets.

# If there are no targets specified with the default command or with command
# line arguments, build everything. Otherwise, build the targets.

targets = set()

for block in blocks:
    if isinstance(block.directive, Default):
        for target in block.directive.targets:
            targets.add(target)

if not targets:
    for block in blocks:
        if isinstance(block.directive, Build):
            targets.add(block.directive.target)

if args.targets:
    targets = set(args.targets)

# But the list of targets is not all we need to start building the code. The
# files might have multiple dependencies and go through different build
# steps. We need to go through the dependency graph, and order them in a way
# that we can build them sequentially without having missing dependencies.

# This is called a "Topological Sort", and you can read more about it on
# Wikipedia.

build_list = []  # Ordered list of how to build things

perm = set()  # Permanent marker
temp = set()  # Temporary marker
unmarked = targets  # Unmarked nodes, i.e. build targets


def visit(n):
    if n in perm:
        return

    if n in temp:
        print("Cannot sort dependencies")
        sys.exit(1)

    temp.add(n)

    block = get_build(n)
    if block:
        nodes = list(block.directive.deps)
        nodes += block.directive.impl
        nodes += block.directive.order
        for dep in nodes:
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

build_list = list(filter(get_build, build_list))

for i, target in enumerate(build_list):
    # Create directory
    Path(target).parent.mkdir(parents=True, exist_ok=True)

    build = get_build(target)
    rule = get_rule(build.directive.rule)

    # Get the  command from the  rule, and do  a quick variable  substitution to
    # replace the input and output file names.
    cmd = rule.variables["command"]

    cmd = replace_variables(cmd, build)
    cmd = cmd.replace("$in", " ".join(build.directive.deps))
    cmd = cmd.replace("$out", target)

    progress = f"[{i+1}/{len(build_list)}]"

    # If the verbose flag is passed, print the command that we are about to run
    if args.verbose:
        print(progress, cmd)
    else:
        print(progress, build.directive.rule.upper(), target)

    # If we are not in a dry run, execute the command
    if not args.dry_run:
        os.system(cmd)
