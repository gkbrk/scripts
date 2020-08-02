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

PATH = sys.argv[1]


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


class Ledger:
    def __init__(self):
        self.commodities = []
        self.accounts = defaultdict(lambda: defaultdict(lambda: Decimal(0)))

    def process_block(self, block):
        if not block:
            return

        if block.name == "commodity":
            com = block.arg.split(" ", 1)
            self.commodities.append(com)
        elif block.name == ";":
            # Comment
            return
        elif block.name == "txn":
            self.process_transaction(block)
        else:
            print(f"[WARNING] Unknown directive '{block.name}'")

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


ledger = Ledger()

for block in read_blocks(PATH):
    ledger.process_block(block)

total = defaultdict(lambda: Decimal())
for name in sorted(ledger.accounts):
    if not name.startswith(sys.argv[2]):
        continue
    print(name)
    for com in sorted(ledger.accounts[name]):
        amt = ledger.accounts[name][com]
        total[com] += amt
        if amt != 0:
            print(f"    {amt} {com}")

print("\nTotal:")
for com in total:
    amt = total[com]
    if amt != 0:
        print(f"  {amt} {com}")

ledger.consistency_check()
