#!/usr/bin/env python3
import os
import time

import numpy as np


class DSP:
    def __init__(self, rate=8000, path="/dev/dsp"):
        self.rate = rate
        self.f = os.open(path, os.O_WRONLY)
        self.s = 0

    def write(self, s):
        s = np.interp(s, [-1, 1], [0, 255])
        s = int(s)
        os.write(self.f, bytes([s]))
        self.s += 1

    def sine(self, freq, amp=0.5):
        s = np.sin(freq * np.pi * 2.0 * self.time) * amp
        self.write(s)

    def sine_duration(self, freq, duration, amp=0.5):
        for _ in self.duration(duration):
            self.sine(freq, amp)

    @property
    def time(self):
        return self.s / self.rate

    def duration(self, duration):
        start = self.time
        while self.time < start + duration:
            yield


def ac_plugged():
    with open("/sys/class/power_supply/AC/online", "r") as ac:
        return ac.read().strip() == "1"


dsp = DSP()

while True:
    if not ac_plugged():
        dsp.sine_duration(0, 1)
        for _ in range(3):
            dsp.sine_duration(1000, 0.05)
            dsp.sine_duration(0, 0.04)
        dsp.sine_duration(0, 2)
    time.sleep(1)
