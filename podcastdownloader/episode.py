#!/usr/bin/env python3

import time
from typing import Dict
from enum import Enum
import re
import os
import pathlib
import requests
import requests.exceptions
import mutagen
import mutagen.easyid3


class Status(Enum):
    blank = 0
    pending = 1
    downloaded = 2


class PodcastException(Exception):
    pass


class Episode:
    def __init__(self, feed_dict: Dict, podcast: str):
        self.feed_entry = feed_dict
        self.podcast = podcast
        self.status = Status.blank
        self.download_link = None

    def parseFeed(self):
        self.title = re.sub(r'(/|\0)', '', self.feed_entry['title'])
        if 'links' in self.feed_entry:
            for link in self.feed_entry['links']:
                if re.match('audio*', link['type']):
                    self.download_link = link['href']
                    break
        elif 'link' in self.feed_entry:
            self.download_link = self.feed_entry['link']

        if not self.download_link:
            raise PodcastException(
                'No download link found for episode {} in podcast {}'.format(
                    self.title, self.podcast))

        r = requests.head(self.download_link, allow_redirects=True)
        self.file_type = r.headers['content-type']
        self.published = self.feed_entry['published_parsed']
        self.id = self.feed_entry['id']
        self.status = Status.pending

    def calcPath(self, dest_folder):
        intended_path = pathlib.Path(dest_folder, self.podcast)
        self.path = None
        if self.file_type == 'audio/mp4':
            self.path = pathlib.Path(intended_path, self.title + '.m4a')
        elif self.file_type == 'audio/mpeg':
            self.path = pathlib.Path(intended_path, self.title + '.mp3')
        if self.path is None:
            raise PodcastException('Cannot determine filename with codec {}'.format(self.file_type))

    def checkExistence(self):
        if os.path.exists(self.path) is True:
            self.status = Status.downloaded

    def download(self):
        # this is a rate-limiting loop in case the connection is reset
        attempts = 1
        while True:
            try:
                content = requests.get(self.download_link).content
                break
            except (requests.exceptions.ChunkedEncodingError, requests.exceptions.ConnectionError):
                if attempts >= 10:
                    print('Episode {} failed to download'.format(self.title))
                    return
                time.sleep(30 * attempts)
                attempts += 1

        with open(self.path, 'wb') as episode_file:
            episode_file.write(content)
            self.status = Status.downloaded

        try:
            tag_file = mutagen.File(self.path, easy=True)
            try:
                tag_file.add_tags()
            except mutagen.MutagenError:
                pass

            tag_file['title'] = self.title
            tag_file['album'] = self.podcast
            tag_file.save()
        except mutagen.MutagenError:
            # just fail silently for now, the tags are a pain
            pass
