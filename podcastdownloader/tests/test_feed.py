#!/usr/bin/env python3

import pytest
from podcastdownloader.feed import Feed


@pytest.fixture
def feed():
    return Feed('https://rss.art19.com/wecrashed')


def test_fetchRSS(feed):
    feed.fetch_rss()
    assert feed.title == 'WeCrashed: The Rise and Fall of WeWork'


def test_extractEpisodes(feed):
    feed.fetch_rss()
    feed.extract_episodes(-1)
    assert len(feed.feed_episodes) == 9
