#!/usr/bin/env python3
# coding=utf-8
import asyncio
from pathlib import Path

import aiohttp
import pytest
import hashlib
from unittest.mock import MagicMock
from podcastdownloader.episode import Episode
from podcastdownloader.exceptions import EpisodeException, TagEngineError


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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('test_url',
     'expected_hash'),
    (('https://sphinx.acast.com/p/open/s/5fc574d8d429ec34a8292b1c/e/621d127983ff8c00129dd5c6/media.mp3',
      ''),
     ('https://b0c2ddc39d13e1c0ddad-93a52a5bc9e7cc06050c1a999beb3694.'
      'ssl.cf1.rackcdn.com/20847573b558163630f6343f3707b637-80.png',
     '69cce47bd5ef08359a1def41f4cd132b',
      ),
     ))
async def test_episode_download(test_url: str, expected_hash: str, tmp_path: Path):
    async with aiohttp.ClientSession(
        headers={
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:103.0) Gecko/20100101 Firefox/103.0',
        },
    ) as session:
        mock_episode = MagicMock()
        mock_episode.url = test_url
        out_path = Path(tmp_path, 'test')
        mock_episode.file_path = out_path
        try:
            await Episode.download(mock_episode, session)
        except TagEngineError:
            pass
        test_hash = hashlib.md5()
        test_hash.update(out_path.read_bytes())
        test_hash = test_hash.hexdigest()
        assert test_hash == expected_hash
