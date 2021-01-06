#!/usr/bin/env python3

import pytest

from podcastdownloader.episode import Episode, EpisodeStatus
from podcastdownloader.exceptions import EpisodeException


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


def test_parse_RSS(episode: Episode):
    episode.parse_rss_entry()
    assert episode.title == 'Bad Test Title'
    assert episode.download_link == 'https://dts.podtrac.com/redirect.mp3/chtbl.com/track/9EE2G/pdst.fm/e/rss.art19.com/episodes/b58e6644-0b5d-492b-ad4a-a773bc701b81.mp3'
    assert episode.file_type == 'audio/mpeg'
    assert episode.status == EpisodeStatus.PENDING


def test_path_calc(episode: Episode):
    episode.title = 'test title'
    episode.file_type = 'audio/mpeg'
    episode.calculate_file_path('testdirectory')
    assert str(episode.path) == 'testdirectory/test podcast/test title.mp3'


@pytest.mark.parametrize(('test_value', 'expected'), (('audio/mp4', '.m4a'),
                                                      ('audio/mp3', '.mp3'),
                                                      ('audio/mpeg', '.mp3'),
                                                      ('audio/flac', '.flac'),
                                                      ('audio/aac', '.aac'),
                                                      ('audio/ogg', '.opus'),
                                                      ('audio/mpeg4-generic', '.aac')))
def test_path_suffix(episode: Episode, test_value: str, expected: str):
    episode.title = ''
    episode.file_type = test_value
    episode.calculate_file_path('.')
    assert str(episode.path).endswith(expected)


@pytest.mark.parametrize('test_value', ('audio/example',
                                        'audio/random',
                                        'video/mp4'))
def test_path_unknown_mimetype(episode: Episode, test_value: str):
    episode.title = ''
    episode.file_type = test_value
    with pytest.raises(EpisodeException):
        episode.calculate_file_path('.')
