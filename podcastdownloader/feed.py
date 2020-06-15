#!/usr/bin/env python3

'''Class for feeds'''

import feedparser
from podcastdownloader.episode import Episode

class Feed:
    def __init__(self, url:str):
        self.url = url
        self.feed_episodes = []
        self.downloaded_episodes = []
    def getFeed(self):
        self.feed = feedparser.parse(self.url)
        self.title = self.feed['feed']['title']
        for entry in self.feed['entries']:
            self.feed_episodes.append(Episode(entry))
        