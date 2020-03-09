#!/usr/bin/env python3
import socket
import time


class Client:
    def __init__(self):
        self.socket = socket.socket()
        self.recv_buffer = b""
        self.send_buffer = b""
        self.addr = None

    def connect(self, addr=("127.0.0.1", 5432)):
        self.addr = addr
        self.socket.connect(addr)
        self.socket.settimeout(0)

    def subscribe(self, channel):
        self.send_buffer += b"S "
        self.send_buffer += channel.encode("utf-8")
        self.send_buffer += b"\n"

    def unsubscribe(self, channel):
        self.send_buffer += b"U "
        self.send_buffer += channel.encode("utf-8")
        self.send_buffer += b"\n"

    def publish(self, channel, data):
        self.send_buffer += b"P "
        self.send_buffer += channel.encode("utf-8")
        self.send_buffer += b" "
        try:
            self.send_buffer += data.encode("utf-8")
        except:
            self.send_buffer += data
        self.send_buffer += b"\n"

    def messages(self, timeout=0):
        self.socket.settimeout(timeout)

        try:
            data = self.socket.recv(4096)
            if data:
                self.recv_buffer += data
        except socket.error:
            pass

        while b"\n" in self.recv_buffer:
            line, self.recv_buffer = self.recv_buffer.split(b"\n", 1)

            channel, data = line.split(b" ", 1)
            yield channel, data

    def send_messages(self, timeout=0):
        if self.send_buffer:
            self.socket.settimeout(timeout)
            try:
                n = self.socket.send(self.send_buffer)
                self.send_buffer = self.send_buffer[n:]
            except socket.error:
                pass


class Connection:
    def __init__(self, connections, sock):
        self.subscribed = []
        self.recv_buffer = b""
        self.send_buffer = b""
        self.connections = connections
        self.sock = sock

    def recv_data(self, data):
        self.recv_buffer += data
        while b"\n" in self.recv_buffer:
            line, self.recv_buffer = self.recv_buffer.split(b"\n", 1)
            self.__on_line(line)

    def __on_line(self, line):
        cmd, data = line.split(b" ", 1)
        if cmd == b"S":
            self.subscribed.append(data.strip())
        elif cmd == b"U":
            self.subscribed.remove(data.strip())
        elif cmd == b"P":
            channel, data = data.split(b" ", 1)
            for conn in self.connections:
                if channel in conn.subscribed or b"*" in conn.subscribed:
                    conn.send_buffer += channel
                    conn.send_buffer += b" "
                    conn.send_buffer += data
                    conn.send_buffer += b"\n"


def runtime_loop():
    l = socket.socket()
    l.setblocking(False)
    l.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    l.bind(("127.0.0.1", 5432))
    l.listen()

    connections = []
    while True:
        time.sleep(0.005)
        try:
            s, _ = l.accept()
            s.setblocking(False)
            c = Connection(connections, s)
            connections.append(c)
        except socket.error:
            pass

        for conn in list(connections):
            try:
                data = conn.sock.recv(4096)
                if data:
                    conn.recv_data(data)
                else:
                    connections.remove(conn)
            except socket.error:
                pass

            if conn.send_buffer:
                try:
                    n = conn.sock.send(conn.send_buffer)
                    if n == 0:
                        connections.remove(conn)
                        continue
                    conn.send_buffer = conn.send_buffer[n:]
                except socket.error:
                    pass


if __name__ == "__main__":
    runtime_loop()
