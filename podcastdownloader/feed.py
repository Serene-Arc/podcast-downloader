#!/usr/bin/env python3

'''Class for feeds'''

import os
import pathlib

import feedparser
import requests
import requests.exceptions

from podcastdownloader.episode import Episode, Status
from podcastdownloader.exceptions import FeedException


class Feed:
    def __init__(self, url: str):
        self.url = url
        self.feed_episodes = []
        self.downloaded_episodes = []

    def __fetch_rss(self):
        try:
            response = requests.get(self.url, timeout=120)
            if response.status_code != 200:
                raise FeedException('Failed to download feed with status: {}'.format(response.status_code))
            self.feed = response.content
        except requests.exceptions.Timeout:
            raise FeedException('Failed to get feed at {}'.format(self.url))
            return

    def parseRSS(self, episode_limit, destination, write_flag):
        self.__fetch_rss()
        self.feed = feedparser.parse(self.feed)
        self.title = self.feed['feed']['title'].encode('utf-8').decode('ascii', 'ignore')

        self.__makeDirectory(destination)
        if episode_limit == -1:
            episode_limit = len(self.feed['entries'])
        for entry in self.feed['entries'][:episode_limit]:
            self.feed_episodes.append(Episode(entry, self.title))

        # if there's an exception in the feed from feedparser, then the entire
        # object becomes unpicklable and wont work with multiprocessing. it still
        # seems to get the episodes most of the time so easier to wipe it
        self.feed = None

    def __makeDirectory(self, destination):
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
