#!/usr/bin/env python3
import subprocess
import tempfile
import threading
from pathlib import Path
import time
import argparse
import signal
from typing import Iterable
import os
import sys

# TODO: Multiple outputs (streaming and recording for example)
# TODO: Saving the inputs to separate files for editing (webcam, audio, screen)
# TODO: Load configuration from JSON file
# TODO: Graphviz visualization of the filter graph
# TODO: Some sort of UI?

output_filename = time.strftime("recording-%Y-%m-%d-%H-%M-%S.mkv", time.gmtime())

parser = argparse.ArgumentParser(
    description="Leo's screen recorder",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)

parser.add_argument("--enable-webcam", action="store_true", help="Enable webcam capture")
parser.add_argument("--enable-datetime", action="store_true", help="Display datetime on screen")
parser.add_argument("--enable-microphone", action="store_true", help="Enable microphone capture")
parser.add_argument("--enable-computer-audio", action="store_true", help="Enable computer audio capture")
parser.add_argument("--ffmpeg-stdout", action="store_true", help="Show ffmpeg stdout")
parser.add_argument("--output", "-o", type=str, default=output_filename, help="Output file")

args = parser.parse_args()

class FilterGraph:
    def __init__(self):
        self._last_id = 0
        self._input_id = 0
        self._filters = []

    def insert(self, inputs: Iterable[str], filter: str) -> str:
        self._last_id += 1
        inputs_str = "".join([f"[{i}]" for i in inputs])
        l = f"{inputs_str}{filter}[graph_{self._last_id}]"
        self._filters.append(l)
        return f"graph_{self._last_id}"

    def input(self) -> str:
        i = self._input_id
        self._input_id += 1
        return str(i)

    @property
    def graph(self) -> str:
        return ";\n".join(self._filters)
    
with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)

    if args.enable_datetime:
        time_path = tmp / "time.txt"
        time_path.touch()

        def datetime_thread():
            dt_tmp = time_path.with_suffix(".tmp")
            format = "%Y%m%d.%H%M%S"
            while True:
                t = time.gmtime()
                t = time.strftime(format, t)
                dt_tmp.write_text(t)
                dt_tmp.rename(time_path)
                time.sleep(0.5)

        threading.Thread(target=datetime_thread, daemon=True).start()

    graph = FilterGraph()

    cmd: list[str] = []

    cmd.append("ffmpeg")

    # Screen capture from X11
    cmd.extend(("-f", "x11grab"))
    cmd.extend(("-framerate", "60"))
    cmd.extend(("-video_size", "1920x1050"))
    cmd.extend(("-thread_queue_size", "4096"))
    cmd.extend(("-i", ":0.0"))
    screen = graph.input()
    screen = graph.insert([screen], "null")

    # Webcam capture
    if args.enable_webcam:
        cmd.extend(("-f", "v4l2"))
        cmd.extend(("-video_size", "320x180"))
        cmd.extend(("-thread_queue_size", "4096"))
        cmd.extend(("-ts", "mono2abs"))
        cmd.extend(("-isync", "0"))
        cmd.extend(("-i", "/dev/video0"))
        webcam = graph.input()
        screen = graph.insert([screen, webcam], "overlay=main_w-overlay_w:main_h-overlay_h")

    # Datetime overlay
    if args.enable_datetime:
        screen = graph.insert(
            [screen],
            f"drawtext=fontfile=/usr/share/fonts/TTF/Iosevka-Regular.ttf:textfile={time_path}:reload=1:fontcolor=white:fontsize=14:box=1:boxcolor=black@0.85:boxborderw=5:x=(w-text_w-10):y=(h-text_h-10)",
        )

    audio = graph.insert([], "anullsrc=r=48000:cl=mono")

    # Audio capture from default pulseaudio device
    if args.enable_microphone:
        cmd.extend(("-f", "pulse"))
        cmd.extend(("-thread_queue_size", "4096"))
        cmd.extend(("-isync", "0"))
        cmd.extend(("-i", "default"))
        mic = graph.input()
        mic = graph.insert([mic], "aresample=async=48000")
        audio = graph.insert([audio, mic], "amix=inputs=2:weights=1 1:normalize=0")

    # Computer audio capture
    if args.enable_computer_audio:
        cmd.extend(("-f", "pulse"))
        cmd.extend(("-thread_queue_size", "4096"))
        cmd.extend(("-isync", "0"))
        cmd.extend(("-i", "@DEFAULT_MONITOR@"))
        computer_audio = graph.input()
        computer_audio = graph.insert([computer_audio], "aresample=async=48000")
        audio = graph.insert([audio, computer_audio], "amix=inputs=2:weights=1 1:normalize=0")

    print(graph.graph)

    cmd.extend(("-filter_complex", graph.graph))

    cmd.extend(("-map", f"[{screen}]"))  # Video
    cmd.extend(("-map", f"[{audio}]"))  # Audio

    cmd.extend(("-f", "flv"))
    cmd.extend(("-preset", "superfast"))
    cmd.extend(("-c:v", "libx264"))
    cmd.extend(("-c:a", "aac"))
    cmd.extend(("-pix_fmt", "yuv420p"))
    cmd.extend(("-vb", "1000k"))
    cmd.append(Path("url.txt").read_text().strip())

    # Output
    # cmd.extend(("-f", "mp4"))
    # cmd.extend(("-preset", "veryfast"))
    # cmd.extend(("-c:a", "aac"))
    # cmd.append("-y")
    # cmd.append('out.mkv')

    # List of ffmpeg MP4 presets: ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow, placebo

    ffmpeg_stdout = subprocess.DEVNULL
    ffmpeg_stderr = subprocess.DEVNULL

    if args.ffmpeg_stdout:
        ffmpeg_stdout = None
        ffmpeg_stderr = None

    p = subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=ffmpeg_stdout,
        stderr=ffmpeg_stderr,
    )
    while True:
        try:
            line = input().strip()
        except EOFError:
            os.kill(p.pid, signal.SIGKILL)
            break
        except KeyboardInterrupt:
            os.kill(p.pid, signal.SIGKILL)
            break

        if line == "args":
            print(sys.argv[1:])
            continue

        if line == "help":
            print(parser.format_help())
            continue

        if line == "restart":
            os.kill(p.pid, signal.SIGKILL)
            p.wait()
            os.execv(sys.argv[0], sys.argv)

        if line.split()[0] == "restart-with":
            os.kill(p.pid, signal.SIGKILL)
            p.wait()
            args = line.split()[1:]
            os.execv(sys.argv[0], [sys.argv[0]] + args)

        if line == "kill":
            print("Terminating ffmpeg")
            os.kill(p.pid, signal.SIGKILL)
            break

        if line == "quit":
            p.terminate()
            p.wait()
            break
