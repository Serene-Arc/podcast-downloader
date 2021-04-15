#!/usr/bin/env python3

import logging
import pathlib

import podcastdownloader.feed as feed

logger = logging.getLogger(__name__)


def _write_audacious(feed: feed.Feed):
    with open(pathlib.Path(feed.directory, 'episode_playlist.audpl'), 'w') as file:
        file.write(f'title={feed.title}\n'.replace(' ', '%20'))
        for episode in reversed(feed.feed_episodes):
            try:
                file.write(f'uri=file://{episode.path}\n'.replace(' ', '%20'))
                file.write(f'title={episode.title}\n'.replace(' ', '%20'))
            except AttributeError:
                logger.warning(f'Could not write {episode.title} to playlist')


def _write_text(feed: feed.Feed):
    with open(pathlib.Path(feed.directory, 'episode_list.txt'), 'w') as file:
        for entry in reversed(feed.feed_episodes):
            file.write(entry.title + '\n')


def _write_m3u(feed: feed.Feed):
    with open(pathlib.Path(feed.directory, 'episode_playlist.m3u'), 'w') as file:
        file.write('#EXTM3U\n')
        for episode in reversed(feed.feed_episodes):
            try:
                file.write('./' + episode.path.name + '\n')
            except AttributeError:
                logger.warning(f'Could not write {episode.title} to playlist')


def write_episode_playlist(feed: feed.Feed, write_choices: list[str]):
    for format_choice in write_choices:
        if format_choice == 'audacious':
            _write_audacious(feed)
        elif format_choice == 'text':
            _write_text(feed)
        elif format_choice == 'm3u':
            _write_m3u(feed)
