#!/usr/bin/python
import time

block_active = False

domains = [
        "www.reddit.com",
        "news.ycombinator.com",
        "www.youtube.com",
]

def unblock(hosts, domain):
    for i, host in enumerate(hosts):
        if len(host) > 0 and host[0] != "#" and len(host.split()) == 2 and host.split()[1] == domain:
            hosts[i] = "#" + host

def block(hosts, domain):
    blocked = False

    for i, host in enumerate(hosts):
        if len(host.split()) == 2 and host.split()[1] == domain:
            blocked = True

            if host[0] == "#":
                hosts[i] = host[1:]

    if not blocked:
        hosts.append("127.0.0.1 {}".format(domain))

if block_active:
    t = time.localtime()
    if t.tm_hour >= 23 or t.tm_hour <= 6:
        f = block
    else:
        f = unblock
else:
    f = unblock

with open("/etc/hosts") as hfile:
    hosts = [line.strip() for line in hfile]

for domain in domains:
    f(hosts, domain)

with open("/etc/hosts", "w") as hfile:
    for h in hosts:
        hfile.write(h)
        hfile.write("\n")

