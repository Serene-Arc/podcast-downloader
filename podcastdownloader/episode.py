#!/usr/bin/env python3

import os
import pathlib
import re
import time
from enum import Enum
from typing import Dict, Optional

import mutagen
import mutagen.easyid3
import requests
import requests.exceptions

from podcastdownloader.exceptions import EpisodeException


class Status(Enum):
    blank = 0
    pending = 1
    downloaded = 2


max_attempts = 10


def _rate_limited_request(url: str, head_only: bool) -> requests.Response:
    attempts = 1
    global max_attempts
    while True:
        try:
            if head_only:
                response = requests.head(url, timeout=180, allow_redirects=True)
            else:
                response = requests.get(url, timeout=180, allow_redirects=True)
            return response
        except (requests.exceptions.ChunkedEncodingError,
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:
            if attempts > max_attempts:
                raise EpisodeException('Connection was limited/refused: {}'.format(e))
            time.sleep(30 * attempts)
            attempts += 1


class Episode:
    def __init__(self, feed_dict: Dict, podcast: str):
        self.feed_entry = feed_dict
        self.podcast = podcast
        self.status = Status.blank
        self.download_link = None

    def parseRSSEntry(self):
        self.title = re.sub(r'(/|\0)', '', self.feed_entry['title'])
        if 'links' in self.feed_entry:
            for link in self.feed_entry['links']:
                if re.match('audio*', link['type']):
                    self.download_link = link['href']
                    self.file_type = link['type']
                    break
        elif 'link' in self.feed_entry:
            self.download_link = self.feed_entry['link']
            self.file_type = None

        if not self.download_link:
            raise EpisodeException(
                'No download link found for episode {} in podcast {}'.format(
                    self.title, self.podcast))

        if not self.file_type:
            r = _rate_limited_request(self.download_link, True)
            self.file_type = r.headers['content-type']
            r.close()

        self.status = Status.pending

    def calcPath(self, dest_folder: pathlib.Path):
        intended_path = pathlib.Path(dest_folder, self.podcast)
        self.path = None
        if self.file_type == 'audio/mp4' or self.file_type == 'audio/x-m4a':
            self.path = pathlib.Path(intended_path, self.title + '.m4a')
        elif self.file_type == 'audio/mpeg' or self.file_type == 'audio/mp3':
            self.path = pathlib.Path(intended_path, self.title + '.mp3')
        if self.path is None:
            raise EpisodeException('Cannot determine filename with codec {}'.format(self.file_type))

    def checkExistence(self):
        if os.path.exists(self.path) is True:
            self.status = Status.downloaded

    def downloadContent(self):
        content = _rate_limited_request(self.download_link, False).content

        with open(self.path, 'wb') as episode_file:
            episode_file.write(content)
            self.status = Status.downloaded

    def writeTags(self):
        try:
            tag_file = mutagen.File(self.path, easy=True)
            try:
                tag_file.add_tags()
            except mutagen.MutagenError:
                pass

            tag_file['title'] = self.title
            tag_file['album'] = self.podcast
            tag_file.save()

        except mutagen.MutagenError as e:
            raise EpisodeException('Mutagen failed to write the tags: {}'.format(e))
