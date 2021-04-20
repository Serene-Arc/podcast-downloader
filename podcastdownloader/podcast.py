#!/usr/bin/env python3
# coding=utf-8

from pathlib import Path
from typing import Optional

import aiohttp
import feedparser

from podcastdownloader.episode import Episode
from podcastdownloader.exceptions import FeedException


class Podcast:
    def __init__(self, url: str):
        self.url = url
        self.feed: Optional[feedparser.FeedParserDict] = None
        self.name: Optional[str] = None
        self.location: Optional[Path] = None
        self.episodes: Optional[list[Episode]] = None

    async def download_feed(self, session: aiohttp.ClientSession):
        async with session.get(self.url) as response:
            feed_data = await response.text()
        feed = feedparser.parse(feed_data)
        if feed['status'] != 200:
            raise FeedException(f'Could not download feed from {self.url}: {feed["status"]}')
        self.feed = feed
        self.name = feed.feed['feed']['title']
        self.episodes = [Episode.parse_dict(entry, self.name) for entry in self.feed.feed['entries']]
