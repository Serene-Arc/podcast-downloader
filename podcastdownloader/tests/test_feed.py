#!/usr/bin/env python3

import unittest
import podcastdownloader.feed as feed


class testFeed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.feed = feed.Feed('https://rss.art19.com/wecrashed')


if __name__ == "__main__":
    unittest.main()
