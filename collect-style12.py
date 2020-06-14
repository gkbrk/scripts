#!/usr/bin/env python3
import socket

full = False

s = socket.socket()
s.connect(("freechess.org", 5000))

# Not Full: Removing game 166 from observation list.
# Full: You are already observing the maximum number of games.

f = s.makefile('rwb')

f.write(b'guest\n')
f.flush()

for line in f:
    line = line.strip()
    if line.startswith(b'Press return to enter the server'):
        f.write(b'\n')
        f.flush()
        break

f.write(b'set style 12\n')
f.flush()

with open('style12.txt', 'a+') as logfile:
    for line in f:
        line = line.strip()
        if b'Removing game' in line and b'from observation list.' in line:
            full = False
        if b'You are already observing the maximum number of games.' in line:
            full = True
        if not full:
            f.write(b"observe *\r\n")
            f.flush()
        if line.startswith(b'<12>'):
            logfile.write(f"{line.decode('utf-8')}\n")
        print(line)
