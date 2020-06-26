#!/usr/bin/env python3

import unittest
import podcastdownloader.episode as episode


class testEpisode(unittest.TestCase):
    def setUp(self):
        feed_dict = {
            'title': 'Bad /Test\0 Title',
            'links': [
                {'href': 'https://dts.podtrac.com/redirect.mp3/chtbl.com/track/9EE2G/pdst.fm/e/rss.art19.com/episodes/b58e6644-0b5d-492b-ad4a-a773bc701b81.mp3',
                    'length': '4690337',
                    'rel': 'enclosure',
                    'type': 'audio/mpeg'}]}
        self.episode = episode.Episode(feed_dict, 'test podcast')

    def test_parseRSS(self):
        self.episode.parseRSSEntry()
        self.assertEquals(self.episode.title, 'Bad Test Title')
        self.assertEquals(
            self.episode.download_link,
            'https://dts.podtrac.com/redirect.mp3/chtbl.com/track/9EE2G/pdst.fm/e/rss.art19.com/episodes/b58e6644-0b5d-492b-ad4a-a773bc701b81.mp3')
        self.assertEquals(self.episode.file_type, 'audio/mpeg')
        self.assertEquals(self.episode.status, episode.Status.pending)

    def test_pathCalc(self):
        self.episode.title = 'test title'
        self.episode.file_type = 'audio/mpeg'
        self.episode.calcPath('testdirectory')
        self.assertEquals(str(self.episode.path), 'testdirectory/test podcast/test title.mp3')


if __name__ == "__main__":
    unittest.main()
