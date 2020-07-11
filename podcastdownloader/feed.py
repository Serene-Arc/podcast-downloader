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

    def __download_rss(self):
        try:
            response = requests.get(self.url, timeout=120)
            if response.status_code != 200:
                raise FeedException('Failed to download feed with status: {}'.format(response.status_code))
            self.feed = response.content
        except requests.exceptions.Timeout:
            raise FeedException('Failed to get feed at {}'.format(self.url))
            return

    def fetchRSS(self):
        self.__download_rss()
        self.feed = feedparser.parse(self.feed)
        self.title = self.feed['feed']['title'].encode('utf-8').decode('ascii', 'ignore')

    def extractEpisodes(self, episode_limit: int):
        if episode_limit == -1:
            episode_limit = len(self.feed['entries'])
        for entry in self.feed['entries'][:episode_limit]:
            self.feed_episodes.append(Episode(entry, self.title))

    def makeDirectory(self, destination: pathlib.Path):
        self.directory = pathlib.Path(destination, self.title)
        if not self.directory.exists():
            os.mkdir(self.directory)


if __name__ == "__main__":
    import pathlib
    import os

    feed = Feed(input('Enter a feed URL: '))
    destination = input('Enter a destination location: ')

    print('Getting feed...')
    feed.fetchRSS()
    feed.makeDirectory(destination)
    feed.extractEpisodes(-1)

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
            ep.verifyDownload()
        if ep.status == Status.pending:
            ep.downloadContent()
            ep.writeTags()
