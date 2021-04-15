#!/usr/bin/env python3

import os
import pathlib
import re
import ssl
import time
from enum import Enum, auto
from typing import Optional

import requests
import requests.exceptions

from podcastdownloader.exceptions import EpisodeException


class EpisodeStatus(Enum):
    BLANK = auto()
    PENDING = auto()
    DOWNLOADED = auto()
    CORRUPTED = auto()


max_attempts = 10


def _rate_limited_request(url: str, head_only: bool) -> requests.Response:
    url = url.strip()
    attempts = 1
    global max_attempts
    while True:
        try:
            if head_only:
                response = requests.head(url, timeout=180, allow_redirects=True)
            else:
                response = requests.get(url, timeout=180, allow_redirects=True)
            return response

        except (requests.exceptions.RequestException, ssl.SSLError) as e:
            if attempts > max_attempts:
                raise EpisodeException(f'Connection was limited/refused: {e}')
            time.sleep(30 * attempts)
            attempts += 1


class Episode:
    def __init__(self, feed_dict: dict, podcast: str):
        self.feed_entry = feed_dict
        self.podcast = podcast
        self.status = EpisodeStatus.BLANK
        self.download_link: Optional[str] = None
        self.title: Optional[str] = None
        self.file_type: Optional[str] = None
        self.path: Optional[pathlib.Path] = None

    def parse_rss_entry(self):
        self.title = re.sub(r'[/\0]', '', self.feed_entry['title'])
        self._find_download_link()
        self.status = EpisodeStatus.PENDING

    def _find_download_link(self):
        if 'links' in self.feed_entry:
            for link in self.feed_entry['links']:
                if 'type' in link and re.match('audio.*', link['type']):
                    self.download_link = link['href']
                    self.file_type = link['type']
                    break
        elif 'link' in self.feed_entry:
            self.download_link = self.feed_entry['link']
            self.file_type = None
        else:
            raise EpisodeException(f'No download link found for episode {self.title} in podcast {self.podcast}')
        if not self.file_type:
            r = _rate_limited_request(self.download_link, True)
            self.file_type = r.headers['content-type']
            r.close()

    def calculate_file_path(self, dest_folder: pathlib.Path):
        intended_path = pathlib.Path(dest_folder, self.podcast)
        self.path = None
        self.file_type = self.file_type.lower()

        # Use MIME types to determine filename
        if self.file_type in ('audio/mp4', 'audio/x-m4a'):
            suffix = '.m4a'
        elif self.file_type in ('audio/mpeg', 'audio/mp3', 'audio/mpa', 'audio/mpa-robust'):
            suffix = '.mp3'
        elif self.file_type in (
            'audio/aac',
            'audio/aacp',
            'audio/3gpp',
            'audio/3gpp2',
            'audio/mp4a-latm',
            'audio/mpeg4-generic',
        ):
            suffix = '.aac'
        elif self.file_type in ('audio/flac', 'audio/x-flac'):
            suffix = '.flac'
        elif self.file_type == 'audio/wav':
            suffix = '.wav'
        elif self.file_type in ('audio/ogg', 'audio/opus'):
            suffix = '.opus'
        else:
            raise EpisodeException(f'Cannot determine filename with codec {self.file_type}')
        self.path = pathlib.Path(intended_path, self.title + suffix)

    def _get_download_size(self) -> int:
        r = _rate_limited_request(self.download_link, True)
        return int(r.headers['content-length'])

    def verify_download_file(self):
        expected_size = self._get_download_size()
        if self.path.exists():
            reported_filesystem_size = self.path.stat().st_size
            # set the tolerance as a percent of the filesize
            if abs(reported_filesystem_size - expected_size) >= (expected_size * 0.02):
                self.status = EpisodeStatus.CORRUPTED

    def check_existence(self):
        if os.path.exists(self.path) is True:
            self.status = EpisodeStatus.DOWNLOADED

    def download_content(self):
        content = _rate_limited_request(self.download_link, False).content
        with open(self.path, 'wb') as episode_file:
            episode_file.write(content)
            self.status = EpisodeStatus.DOWNLOADED
