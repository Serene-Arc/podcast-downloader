#!/usr/bin/env python3
# coding=utf-8
import asyncio

import aiohttp
import pytest

from podcastdownloader.episode import Episode
from podcastdownloader.exceptions import EpisodeException


@pytest.fixture(scope='session')
def client_session() -> aiohttp.ClientSession:
    out = aiohttp.ClientSession()
    return out


@pytest.mark.parametrize(('test_link_dict', 'expected'), (
    ([{
        'rel': 'alternate',
        'type': 'text/html',
        'href': 'http://evenmorenewspodcast.com/usa-still-leaving-afghanistan-still-shooting'
        '-unarmed-people-w-christopher-rivas-ep-142',
    },
        {
        'length': '54468321',
        'type': 'audio/mpeg',
        'href': 'https://dts.podtrac.com/redirect.mp3/chtbl.com/track/242FB3/'
        'traffic.libsyn.com/secure/evenmorenews/EMN_Ep142.mp3?dest-id=695480',
        'rel': 'enclosure',
    }],
        'https://dts.podtrac.com/redirect.mp3/chtbl.com/track/242FB3/'
        'traffic.libsyn.com/secure/evenmorenews/EMN_Ep142.mp3?dest-id=695480'),
))
def test_episode_find_url(test_link_dict: list[dict], expected: str):
    test_dict = {'links': test_link_dict, }
    result = Episode._find_url(test_dict)
    assert result == expected


@pytest.mark.parametrize('test_link_dict', (
    [{
        'rel': 'alternate',
        'type': 'text/html',
        'href': 'http://evenmorenewspodcast.com/usa-still-leaving-afghanistan-still-shooting'
        '-unarmed-people-w-christopher-rivas-ep-142',
    }],
))
def test_episode_find_url_bad(test_link_dict: list[dict]):
    test_dict = {
        'links': test_link_dict,
        'title': 'test',
    }
    with pytest.raises(EpisodeException):
        Episode._find_url(test_dict)


@pytest.mark.parametrize(('test_url', 'expected'), (
    ('https://www.example.com/test.png', '.png'),
    ('https://www.example.com/test.mp3', '.mp3'),
    ('https://www.example.com/random/test.flac', '.flac'),
    ('https://www.example.com/test.mp3?test=value', '.mp3'),
    ('https://www.example.com/test.mp3?test=value#test', '.mp3'),
    ('https://www.example.com/test.aac', '.aac'),
))
def test_determine_file_extension_from_url(test_url: str, expected: str, client_session):
    result = asyncio.run(Episode._get_file_extension(test_url, client_session))
    assert result == expected


@pytest.mark.parametrize(('test_name', 'expected'), (
    ('test', 'test'),
    ('te/st', 'test'),
    ('test/test', 'testtest'),
    ('test\0', 'test'),
))
def test_clean_name(test_name: str, expected: str):
    result = Episode._clean_name(test_name)
    assert result == expected
