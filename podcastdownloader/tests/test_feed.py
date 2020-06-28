#!/usr/bin/env python3

import unittest
import podcastdownloader.feed as feed


class testFeed(unittest.TestCase):
    def setUp(self):
        self.feed = feed.Feed('https://rss.art19.com/wecrashed')

    def test_fetchRSS(self):
        self.feed.fetchRSS()
        self.assertEquals(self.feed.title, 'WeCrashed: The Rise and Fall of WeWork')

    def test_extractEpisodes(self):
        self.feed.fetchRSS()
        self.feed.extractEpisodes(-1)
        self.assertEquals(len(self.feed.feed_episodes), 11)


if __name__ == "__main__":
    unittest.main()
