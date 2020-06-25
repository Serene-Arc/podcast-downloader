#!/usr/bin/env python3

'''Class for feeds'''

import feedparser
from podcastdownloader.episode import Episode, PodcastException, Status
import requests
import requests.exceptions
import os
import pathlib


class Feed:
    def __init__(self, url: str):
        self.url = url
        self.feed_episodes = []
        self.downloaded_episodes = []

    def __fetch_rss(self):
        try:
            self.feed = requests.get(self.url, timeout=120).text
        except requests.exceptions.Timeout:
            print('Failed to get feed at {}'.format(self.url))
            return

    def parseRSS(self, episode_limit, destination, write_flag):
        self.__fetch_rss()
        self.feed = feedparser.parse(self.feed)
        self.title = self.feed['feed']['title'].encode('utf-8').decode('ascii', 'ignore')

        self._makeDirectory(destination)
        if episode_limit == -1:
            episode_limit = len(self.feed['entries'])
        for entry in self.feed['entries'][:episode_limit]:
            self.feed_episodes.append(Episode(entry, self.title))

        if write_flag:
            with open(pathlib.Path(destination, self.title, 'episode_list.txt'), 'w') as file:
                for entry in reversed(self.feed['entries']):
                    file.write(entry['title'] + '\n')

        # if there's an exception in the feed from feedparser, then the entire
        # object becomes unpicklable and wont work with multiprocessing. it still
        # seems to get the episodes most of the time so easier to wipe it
        self.feed = None

    def _makeDirectory(self, destination):
        try:
            self.directory = pathlib.Path(destination, self.title)
            os.mkdir(self.directory)
        except FileExistsError:
            pass


if __name__ == "__main__":
    import pathlib
    import os

    feed = Feed(input('Enter a feed URL: '))
    destination = input('Enter a destination location: ')

    print('Getting feed...')
    feed.parseRSS(-1, destination, True)

    existingFiles = []
    print('Scanning existing files...')
    for (dirpath, dirnames, filenames) in os.walk(destination):
        existingFiles.extend([str(pathlib.PurePath(dirpath, filename)) for filename in filenames])

    for ep in feed.feed_episodes:
        print('Parsing episode...')
        ep.parseRSSEntry()
        ep.calcPath(destination)
        if str(ep.path) in existingFiles:
            ep.status = Status.downloaded
        if ep.status == Status.pending:
            ep.downloadContent()
            ep.writeTags()
