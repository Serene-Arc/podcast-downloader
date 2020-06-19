#!/usr/bin/env python3

'''Class for feeds'''

import feedparser
from episode import Episode, PodcastException, Status
import requests
import requests.exceptions


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

    def parseRSS(self):
        self.__fetch_rss()
        self.feed = feedparser.parse(self.feed)
        self.title = self.feed['feed']['title'].encode('utf-8').decode('ascii', 'ignore')
        for entry in self.feed['entries']:
            self.feed_episodes.append(Episode(entry, self.title))

        # if there's an exception in the feed from feedparser, then the entire
        # object becomes unpicklable and wont work with multiprocessing. it still
        # seems to get the episodes most of the time so easier to wipe it
        self.feed = None


if __name__ == "__main__":
    import pathlib
    import os

    feed = Feed(input('Enter a feed URL: '))
    destination = input('Enter a destination location: ')

    print('Getting feed...')
    feed.parseRSS()

    existingFiles = []
    print('Scanning existing files...')
    for (dirpath, dirnames, filenames) in os.walk(destination):
        existingFiles.extend([str(pathlib.PurePath(dirpath, filename)) for filename in filenames])

    dest = pathlib.Path(destination, feed.title)
    if os.path.exists(dest) is False:
        os.mkdir(pathlib.Path(destination, feed.title))

    for ep in feed.feed_episodes:
        print('Parsing episode...')
        ep.parseRSSEntry()
        ep.calcPath(destination)
        if str(ep.path) in existingFiles:
            ep.status = Status.downloaded
        if ep.status == Status.pending:
            # ep.downloadContent()
            pass
