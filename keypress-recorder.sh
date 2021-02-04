#!/bin/sh

REGION=$(slurp)
KB='/dev/input/event5'
KB='/dev/input/event8'
FPS=10
OUTPUT="recording-$(date "+%Y-%m-%d-%H-%M").mkv"

sudo chown "$(whoami)" "${KB}"

block_keypress () {
    cat "${KB}" | head -c1 > /dev/null
}

record_video () {
    ffmpeg -f image2pipe -r "${FPS}" -i - \
    -vf "pad=ceil(iw/2)*2:ceil(ih/2)*2" \
    -codec:v h264 -preset slow -r 30 "${OUTPUT}"
}

while true;
do
    block_keypress
    grim -g "${REGION}" -t jpeg -c -
done | record_video
