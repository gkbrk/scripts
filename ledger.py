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
import os

# File parser


class Block:
    def __init__(self, lines):
        self.lines = lines

    def __bool__(self):
        return len(self.lines) != 0

    @property
    def is_comment(self):
        try:
            return self.lines[0][0] in ";#%|*"
        except Exception:
            return False

    @property
    def date(self):
        try:
            return self.lines[0].split(" ", 2)[0]
        except Exception:
            return "1970-01-01"

    @property
    def name(self):
        try:
            return self.lines[0].split(" ", 2)[1].lower()
        except Exception:
            return ""

    @property
    def arg(self):
        try:
            return self.lines[0].split(" ", 2)[2]
        except Exception:
            return ""

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

            if not line:
                continue

            yield line

    def __iter__(self):
        block = []

        for line in self.lines:
            ind = BlockLexer.indented(line)

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
        self.rates = defaultdict(lambda: Decimal(0))

    def process_block(self, block):
        if not block:
            return

        if block.is_comment:
            return

        if block.name == "nop":
            # No operation
            return
        if block.name == "commodity":
            com = block.arg.split(" ", 1)[0]
            warn_strict(
                f"Duplicate commodity '{com}'", com in self.commodities
            )
            self.commodities.add(com)
        elif block.name == "txn":
            self.process_transaction(block)
        elif block.name == "include":
            for bl in read_blocks(block.arg):
                self.process_block(bl)
        elif block.name == "assert-balance":
            name, amt, com = block.arg.split()
            amt = Decimal(amt)

            bal = self.accounts[name][com]
            warn_strict(
                f"Expected balance for {name} is {amt}, found {bal}",
                bal != amt,
            )
        elif block.name == "balance":
            name, amt, com = block.arg.split()
            amt = Decimal(amt)

            bal = self.accounts[name][com]
            if bal == amt:
                return

            if bal > amt:
                self.accounts["Expenses:ForceBalance"][com] += bal - amt
                self.accounts[name][com] -= bal - amt
            elif amt > bal:
                self.accounts["Income:ForceBalance"][com] -= amt - bal
                self.accounts[name][com] += amt - bal
        elif block.name == "price":
            com1, rate, com2 = block.arg.split()
            self.rates[(com1, com2)] = Decimal(rate)
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
        # print(block)
        # self.consistency_check()

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

        for arg in self.args:
            a = arg.startswith("-")
            if not a:
                accounts.append(arg)
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


def print_table(table, fmt=None):
    table = [[str(x) for x in row] for row in table]
    col_num = len(max(table, key=len))
    col_w = [0 for _ in range(col_num)]

    if not fmt:
        fmt = [">" for _ in range(col_num)]

    for col in range(col_num):
        col_w[col] = len(max(map(lambda x: x[col], table), key=len))

    for row in table:
        for i, col in enumerate(row):
            print(f"{col: {fmt[i]}{col_w[i]}}", end="  ")
        print()


@subcommand("converted-balance")
def convertedbalance():
    accounts = args.filtered_accounts(ledger)

    w = max(accounts, key=len)
    w = len(w)

    rates = ledger.rates
    for _ in range(10):
        for com1, com2 in dict(rates):
            rel = (com1, com2)
            rev = (com2, com1)

            if rates[rev] == 0:
                rates[rev] = 1 / rates[rel]

    def conv_rate(com1, com2):
        q = []
        discovered = set()
        parents = {}

        amt = 1
        discovered.add(com1)
        q.append(com1)

        while len(q):
            v = q.pop()
            if v == com2:
                amt = 1
                n = com2
                while n in parents:
                    amt *= rates[(parents[n], n)]
                    n = parents[n]
                return amt

            for _com1, _com2 in filter(lambda x: x[0] == v, rates):
                if _com2 not in discovered:
                    discovered.add(_com2)
                    q.append(_com2)
                    parents[_com2] = _com1
        return 0

    for target in os.environ.get("CURRENCY", "EUR,TRY,USD").split(","):
        grand_total = 0

        totals = {}
        for name in accounts:
            total = 0
            for com in ledger.accounts[name]:
                amt = ledger.accounts[name][com]
                if amt != 0:
                    conv = conv_rate(com, target)
                    total += amt * conv
            grand_total += total
            if total != 0:
                totals[name] = total

        table = []
        table.append(["Name", "Total", "Currency", "Percentage %"])
        table.append(["----", "-----", "--------", "------------"])
        for name in totals:
            total = totals[name]
            row = []

            row.append(name)
            row.append(f"{total:.2f}")
            row.append(target)

            perc = total / grand_total * 100
            row.append(f"{perc:.2f}")

            table.append(row)
        table.append(["----", "-----", "--------", "------------"])
        table.append(["Total", f"{grand_total:.2f}", target, "100"])
        print_table(table, ["<", ">", "<", ">"])
        print("\n")


args = Arguments()
ledger = Ledger()

blocks = read_blocks(args.file)

for block in sorted(blocks, key=lambda x: x.date):
    ledger.process_block(block)

subcommands[args.action]()
