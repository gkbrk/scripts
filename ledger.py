#!/usr/bin/env python3

# Ledger: Double-entry accounting system
# Copyright (C) 2020 Gokberk Yaltirakli
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
from collections import defaultdict
from decimal import Decimal

# File parser


class Block:
    def __init__(self, lines):
        self.lines = lines

    def __bool__(self):
        return len(self.lines) != 0

    @property
    def name(self):
        return self.lines[0].split(" ", 1)[0].lower()

    @property
    def arg(self):
        return self.lines[0].split(" ", 1)[1]

    @property
    def children(self):
        return self.lines[1:]

    def __repr__(self):
        if self:
            return f"[{self.name}] ({self.arg}) {self.children}"
        return "Block(Empty)"


class BlockLexer:
    def __init__(self, reader):
        self.reader = reader

    @staticmethod
    def indented(line):
        return line.startswith(" ")

    @property
    def lines(self):
        for line in self.reader:
            line = line.rstrip()

            # Inline comments
            line = line.split(";", 1)[0]

            if not line:
                continue

            yield line

    def __iter__(self):
        block = []
        prev = ""

        for line in self.lines:
            ind = BlockLexer.indented(line)
            prev_ind = BlockLexer.indented(prev)

            if ind:
                block.append(line.strip())
            else:
                yield Block(block)
                block = [line]
        yield Block(block)


def read_blocks(path):
    with open(path) as f:
        yield from BlockLexer(f)


# Ledger and bookkeeping logic


def warn_strict(message, condition=True):
    if args.strict and condition:
        print(f"[WARNING] {message}")


class Ledger:
    def __init__(self):
        self.commodities = set()
        self.accounts = defaultdict(lambda: defaultdict(lambda: Decimal(0)))

    def process_block(self, block):
        if not block:
            return

        if block.name == "commodity":
            com = block.arg.split(" ", 1)[0]
            warn_strict(f"Duplicate commodity '{com}'", com in self.commodities)
            self.commodities.add(com)
        elif block.name == ";":
            # Comment
            return
        elif block.name == "txn":
            self.process_transaction(block)
        else:
            warn_strict(f"Unknown directive '{block.name}'")

    def process_transaction(self, block):
        total = defaultdict(lambda: Decimal())

        for line in block.children:
            if len(line.split()) == 1:
                account = line
                for com in total:
                    self.accounts[account][com] -= total[com]
                    total[com] = 0
            else:
                account, amount, commodity = line.split(" ", 2)

                warn_strict(
                    f"Unknown commodity '{commodity}'",
                    commodity not in self.commodities,
                )

                total[commodity] += Decimal(amount)
                self.accounts[account][commodity] += Decimal(amount)

    def consistency_check(self):
        total = defaultdict(lambda: Decimal())

        for name in self.accounts:
            for com in self.accounts[name]:
                amt = self.accounts[name][com]
                total[com] += amt

        for com in total:
            assert total[com] == 0, f"{total[com]} {com}"


# Command line interface


class Arguments:
    def __init__(self, args=None):
        if args is None:
            args = sys.argv[1:]
        self.args = list(args)
        self.file = self.args.pop(0)
        self.action = self.args.pop(0)

    @property
    def accounts(self):
        accounts = []

        prev = ""
        for arg in self.args:
            p = prev.startswith("-")
            a = arg.startswith("-")
            if not p and not a:
                accounts.append(arg)
            prev = arg
        return accounts

    def filtered_accounts(self, ledger):
        accounts = sorted(ledger.accounts)

        if args.accounts:
            act = []
            for account in accounts:
                if any(map(lambda x: account.startswith(x), self.accounts)):
                    act.append(account)
            return act
        return accounts

    @property
    def strict(self):
        return "--strict" in self.args


subcommands = {}


def subcommand(name=None):
    def decorator(func):
        subcommands[name or func.__name__] = func

    return decorator


@subcommand()
def check():
    ledger.consistency_check()


@subcommand()
def accounts():
    for name in args.filtered_accounts(ledger):
        print(name)


@subcommand()
def balance():
    total = defaultdict(lambda: Decimal())
    accounts = args.filtered_accounts(ledger)

    w = max(accounts, key=lambda x: len(x))
    w = len(w)

    for name in accounts:
        for com in sorted(ledger.accounts[name]):
            amt = ledger.accounts[name][com]
            total[com] += amt
            if amt != 0:
                print(f"{name: <{w}}  {amt} {com}")

    print("\nTotal:")
    for com in total:
        amt = total[com]
        if amt != 0:
            print(f"  {amt} {com}")


args = Arguments()
ledger = Ledger()

for block in read_blocks(args.file):
    ledger.process_block(block)

subcommands[args.action]()
