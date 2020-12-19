#!/usr/bin/env python3

import pytest
from podcastdownloader.episode import Episode, EpisodeStatus


@pytest.fixture
def episode():
    feed_dict = {
        'title': 'Bad /Test\0 Title',
        'links': [
            {'href': 'https://dts.podtrac.com/redirect.mp3/chtbl.com/track/9EE2G/pdst.fm/e/rss.art19.com/episodes/b58e6644-0b5d-492b-ad4a-a773bc701b81.mp3',
                'length': '4690337',
                'rel': 'enclosure',
                'type': 'audio/mpeg'}]}
    return Episode(feed_dict, 'test podcast')


def test_parseRSS(episode):
    episode.parse_rss_entry()
    assert episode.title == 'Bad Test Title'
    assert episode.download_link == 'https://dts.podtrac.com/redirect.mp3/chtbl.com/track/9EE2G/pdst.fm/e/rss.art19.com/episodes/b58e6644-0b5d-492b-ad4a-a773bc701b81.mp3'
    assert episode.file_type == 'audio/mpeg'
    assert episode.status == EpisodeStatus.PENDING


def test_pathCalc(episode):
    episode.title = 'test title'
    episode.file_type = 'audio/mpeg'
    episode.calculate_file_path('testdirectory')
    assert str(episode.path) == 'testdirectory/test podcast/test title.mp3'
