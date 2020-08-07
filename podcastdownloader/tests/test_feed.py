#!/usr/bin/env python3

import pytest
from podcastdownloader.feed import Feed


@pytest.fixture
def feed():
    return Feed('https://rss.art19.com/wecrashed')


def test_fetchRSS(feed):
    feed.fetchRSS()
    assert feed.title == 'WeCrashed: The Rise and Fall of WeWork'


def test_extractEpisodes(feed):
    feed.fetchRSS()
    feed.extractEpisodes(-1)
    assert len(feed.feed_episodes) == 9
