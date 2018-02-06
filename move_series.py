#!/usr/bin/env python3
from pathlib import Path
import re
import shutil
import os

download_dir = Path('/home/leonardo/TorrentDownloads/Series/')
series_dir = Path('/home/leonardo/tvshows/Series/')

def parse_filename(name):
    parts = name.split('.')
    name_parts = []

    for part in parts:
        episode = re.match('^S(\d+)E(\d+)$', part)
        if episode:
            break

        name_parts.append(part)

    name = '.'.join(name_parts)
    season = episode.group(1)
    episode = episode.group(2)
    return (name, season, episode)

for downloaded_file in download_dir.glob('**/*.mkv'):
    name, season, episode = parse_filename(downloaded_file.name)
    print('Moving', name, 'Season', season, 'Episode', episode, '...')
    target = series_dir / name / 'S{}'.format(season) / downloaded_file.name
    try:
        os.makedirs(target.parent)
    except:
        pass
    shutil.move(downloaded_file, target)
