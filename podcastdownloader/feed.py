#!/usr/bin/env python3

import os
import pathlib
import ssl
import time
from typing import Optional

import feedparser
import requests
import requests.exceptions

from podcastdownloader.episode import Episode
from podcastdownloader.exceptions import FeedException


def _limited_rate_request(url: str) -> requests.Response:
    url = url.strip()
    attempts = 1
    while True:
        try:
            response = requests.get(url, timeout=180, allow_redirects=True)
            return response
        except (requests.exceptions.RequestException, ssl.SSLError) as e:
            # 3 is a magic number
            # TODO: make this configurable as well
            if attempts > 3:
                raise FeedException(f'Failed to get feed {url}; connection was limited/refused: {e}')
            time.sleep(30 * attempts)
            attempts += 1


class Feed:
    def __init__(self, url: str):
        self.url = url
        self.feed_episodes = []
        self.feed: Optional[feedparser.FeedParserDict] = None
        self.title: Optional[str] = None
        self.directory: Optional[pathlib.Path] = None

    def fetch_rss(self):
        response = _limited_rate_request(self.url)
        self.feed = feedparser.parse(response.content)
        self.title = self.feed['feed']['title'].encode('utf-8').decode('ascii', 'ignore')

    def extract_episodes(self, episode_limit: int):
        if episode_limit == -1:
            episode_limit = len(self.feed['entries'])
        for entry in self.feed['entries'][:episode_limit]:
            self.feed_episodes.append(Episode(entry, self.title))

    def make_directory(self, destination: pathlib.Path):
        self.directory = pathlib.Path(destination, self.title)
        if not self.directory.exists():
            os.mkdir(self.directory)
