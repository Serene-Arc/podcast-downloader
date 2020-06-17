#!/usr/bin/env python3

'''Class for feeds'''

import feedparser
from episode import Episode, PodcastException
import requests
import requests.exceptions


class Feed:
    def __init__(self, url: str):
        self.url = url
        self.feed_episodes = []
        self.downloaded_episodes = []

    def __download_rss(self):
        try:
            self.feed = requests.get(self.url, timeout=120).text
        except requests.exceptions.Timeout:
            print('Failed to get feed at {}'.format(self.url))
            return

    def getFeed(self):
        self.__download_rss()
        self.feed = feedparser.parse(self.feed)
        self.title = self.feed['feed']['title'].encode('utf-8').decode('ascii', 'ignore')
        for entry in self.feed['entries']:
            self.feed_episodes.append(Episode(entry, self.title))

        # if there's an exception in the feed from feedparser, then the entire
        # object becomes unpicklable and wont work with multiprocessing. it still
        # seems to get the episodes most of the time so easier to wipe it
        self.feed = None

    def fillEpisodes(self):
        for episode in self.feed_episodes:
            try:
                episode.parseFeed()
            except PodcastException as e:
                print(e)
