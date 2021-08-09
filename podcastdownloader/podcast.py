#!/usr/bin/env python3
# coding=utf-8

import logging
from pathlib import Path
from typing import Optional

import aiohttp
import aiohttp.client_exceptions
import feedparser
import feedparser.exceptions

from podcastdownloader.episode import Episode
from podcastdownloader.exceptions import FeedException

logger = logging.getLogger(__name__)


class Podcast:
    def __init__(self, url: str):
        self.url = url
        self.feed: Optional[feedparser.FeedParserDict] = None
        self.name: Optional[str] = None
        self.location: Optional[Path] = None
        self.episodes: Optional[list[Episode]] = []

    async def download_feed(self, session: aiohttp.ClientSession):
        try:
            async with session.get(self.url) as response:
                feed_data = await response.content.read()
                if response.status != 200:
                    raise FeedException(f'Failed to download feed from {self.url}: Response code {response.status}')
        except aiohttp.client_exceptions.ClientError as e:
            raise FeedException(f'Failed to download feed from {self.url}: {e}')
        feed = feedparser.parse(feed_data)
        if feed['bozo']:
            raise FeedException(f'Feed from {self.url} was malformed')
        self.feed = feed
        self.name = feed['feed']['title']
        self.episodes = [Episode.parse_dict(entry, self.name) for entry in self.feed['entries']]
