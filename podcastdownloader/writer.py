#!/usr/bin/env python3

import pathlib


def __writeAudacious(feed):
    with open(pathlib.Path(feed.directory, 'episode_playlist.audpl'), 'w') as file:
        file.write('title={}\n'.format(feed.title).replace(' ', '%20'))
        for episode in reversed(feed.feed_episodes):
            try:
                file.write('uri=file://{}\n'.format(episode.path).replace(' ', '%20'))
                file.write('title={}\n'.format(episode.title).replace(' ', '%20'))
            except AttributeError as e:
                pass


def __writeText(feed):
    with open(pathlib.Path(feed.directory, 'episode_list.txt'), 'w') as file:
        for entry in reversed(feed.episode_list):
            file.write(entry.title + '\n')


def writeEpisode(feed, write_choice):
    if write_choice == 'audacious':
        __writeAudacious(feed)
    elif write_choice == 'text':
        __writeText(feed)
