#!/usr/bin/env python3
# coding=utf-8

import logging
import pathlib

from podcastdownloader.podcast import Podcast

logger = logging.getLogger(__name__)


def _write_m3u(podcast: Podcast):
    podcast_path = podcast.episodes[0].file_path.parent
    podcast_path.mkdir(parents=True, exist_ok=True)
    with open(pathlib.Path(podcast_path, 'episode_playlist.m3u'), 'w') as file:
        file.write('#EXTM3U\n')
        for episode in reversed(podcast.episodes):
            try:
                file.write('./' + episode.file_path.name + '\n')
            except AttributeError:
                logger.warning(f'Could not write {episode.title} to playlist')
    logger.debug(f'M3U playlist for {podcast.name} written')


def write_episode_playlist(podcast: Podcast, write_choices: tuple[str]):
    for format_choice in write_choices:
        if format_choice == 'm3u':
            _write_m3u(podcast)
        else:
            logger.error(f'Unknown playlist format type: {format_choice}')
