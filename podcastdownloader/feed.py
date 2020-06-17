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

    def getFeed(self):
        try:
            rss_feed = requests.get(self.url, timeout=120)
        except requests.exceptions.Timeout:
            print('Failed to get feed at {}'.format(self.url))

        self.feed = feedparser.parse(rss_feed.text)
        self.title = self.feed['feed']['title'].encode('utf-8').decode('ascii', 'ignore')
        for entry in self.feed['entries']:
            self.feed_episodes.append(Episode(entry, self.title))

    def fillEpisodes(self):
        for episode in self.feed_episodes:
            try:
                episode.parseFeed()
            except PodcastException as e:
                print(e)
