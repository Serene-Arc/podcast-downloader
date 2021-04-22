#!/usr/bin/env python3
# coding=utf-8

import logging
import mimetypes
import re
import urllib.parse
from pathlib import Path
from typing import Optional

import aiohttp
import aiohttp.client_exceptions
from multidict import CIMultiDictProxy

from podcastdownloader.exceptions import EpisodeException

logger = logging.getLogger(__name__)


class Episode:
    def __init__(self, title_name: str, episode_url: str, podcast_name: str):
        self.title = self._clean_name(title_name)
        self.url = episode_url
        self.podcast_name = podcast_name
        self.file_path: Optional[Path] = None

    @staticmethod
    def parse_dict(feed_dict: dict, podcast_name: str) -> 'Episode':
        episode_url = Episode._find_url(feed_dict)
        result = Episode(
            feed_dict['title'],
            episode_url,
            podcast_name,
        )
        return result

    @staticmethod
    def _clean_name(name: str) -> str:
        name = re.sub(r'(\0|/)', '', name)
        return name

    @staticmethod
    def _find_url(feed_dict: dict) -> str:
        mime_type_regex = re.compile(r'^audio.*')
        valid_urls = list(filter(lambda u: re.match(mime_type_regex, u['type']), feed_dict['links']))
        if valid_urls:
            return valid_urls[0].get('href')
        else:
            raise EpisodeException('Could not find a valid link')

    @staticmethod
    async def _get_file_extension(url: str, session: aiohttp.ClientSession) -> str:
        url = urllib.parse.urlsplit(url).path
        mime_type = mimetypes.guess_type(url)[0]
        if not mime_type:
            async with session.get(url) as response:
                headers = response.headers
            mime_type = headers.get('Content-Type')
        if not mime_type:
            raise EpisodeException(f'Could not determine MIME type for URL {url}')
        result = mimetypes.guess_extension(mime_type)
        if result:
            return result
        else:
            raise EpisodeException(f'Could not determine file extension for download {url}')

    async def calculate_path(self, destination: Path, session: aiohttp.ClientSession):
        try:
            file_extension = await self._get_file_extension(self.url, session)
            file_name = self.title + file_extension
            self.file_path = Path(destination, self.podcast_name, file_name)
        except (aiohttp.client_exceptions.ClientError, EpisodeException) as e:
            raise EpisodeException(f'Failed to determine path for "{self.title}" from "{self.podcast_name}": {e}')

    async def download(self, session: aiohttp.ClientSession):
        if not self.file_path:
            raise EpisodeException('Episode has no calculated path')
        try:
            async with session.get(self.url) as response:
                if not self.file_path.exists():
                    data = await response.content.read()
                    self.file_path.parent.mkdir(exist_ok=True, parents=True)
                    with open(self.file_path, 'wb') as file:
                        file.write(data)
                    logger.info(f'Downloaded {self.title} in podcast {self.podcast_name}')
                else:
                    logger.debug(f'File already exists at {self.file_path}')
        except aiohttp.client_exceptions.ClientError as e:
            raise EpisodeException(f'Failed to download "{self.title}" from "{self.podcast_name}": {e}')
