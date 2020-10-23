#!/usr/bin/env python3

import pathlib

import podcastdownloader.feed as feed


def __writeAudacious(feed: feed.Feed):
    with open(pathlib.Path(feed.directory, 'episode_playlist.audpl'), 'w') as file:
        file.write('title={}\n'.format(feed.title).replace(' ', '%20'))
        for episode in reversed(feed.feed_episodes):
            try:
                file.write('uri=file://{}\n'.format(episode.path).replace(' ', '%20'))
                file.write('title={}\n'.format(episode.title).replace(' ', '%20'))
            except AttributeError as e:
                pass


def __writeText(feed: feed.Feed):
    with open(pathlib.Path(feed.directory, 'episode_list.txt'), 'w') as file:
        for entry in reversed(feed.feed_episodes):
            file.write(entry.title + '\n')


def __writeM3u(feed: feed.Feed):
    with open(pathlib.Path(feed.directory, 'episode_playlist.m3u'), 'w') as file:
        file.write('#EXTM3U\n')
        for episode in reversed(feed.feed_episodes):
            try:
                file.write(episode.path.name + '\n')
            except AttributeError:
                pass


def writeEpisode(feed: feed.Feed, write_choice: str):
    if write_choice == 'audacious':
        __writeAudacious(feed)
    elif write_choice == 'text':
        __writeText(feed)
    elif write_choice == 'm3u':
        __writeM3u(feed)
