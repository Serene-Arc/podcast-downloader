#!/usr/bin/env python3

import time
from typing import Dict
from enum import Enum
import re
import os
import pathlib
import requests


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
        self.title = self.feed_entry['title']
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
        if self.path is None:
            raise PodcastException('Cannot determine filename')
