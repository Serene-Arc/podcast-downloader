#!/usr/bin/env python3

import logging
import pathlib
from typing import List

import podcastdownloader.feed as feed

logger = logging.getLogger(__name__)


def __writeAudacious(feed: feed.Feed):
    with open(pathlib.Path(feed.directory, 'episode_playlist.audpl'), 'w') as file:
        file.write('title={}\n'.format(feed.title).replace(' ', '%20'))
        for episode in reversed(feed.feed_episodes):
            try:
                file.write('uri=file://{}\n'.format(episode.path).replace(' ', '%20'))
                file.write('title={}\n'.format(episode.title).replace(' ', '%20'))
            except AttributeError as e:
                logger.warning('Could not write {} to playlist'.format(episode.title))


def __writeText(feed: feed.Feed):
    with open(pathlib.Path(feed.directory, 'episode_list.txt'), 'w') as file:
        for entry in reversed(feed.feed_episodes):
            file.write(entry.title + '\n')


def __writeM3u(feed: feed.Feed):
    with open(pathlib.Path(feed.directory, 'episode_playlist.m3u'), 'w') as file:
        file.write('#EXTM3U\n')
        for episode in reversed(feed.feed_episodes):
            try:
                file.write('./' + episode.path.name + '\n')
            except AttributeError:
                logger.warning('Could not write {} to playlist'.format(episode.title))


def writeEpisode(feed: feed.Feed, write_choices: List[str]):
    for format_choice in write_choices:
        if format_choice == 'audacious':
            __writeAudacious(feed)
        elif format_choice == 'text':
            __writeText(feed)
        elif format_choice == 'm3u':
            __writeM3u(feed)
