#!/usr/bin/env python3

import time
from typing import Dict

class Episode:
    def __init__(self, feed_dict:Dict):
        self.feed_entry = feed_dict
    def parseFeed(self):
        self.title = self.feed_entry['title'] 
        self.download_link = self.feed_entry['links']['href']
        self.published = self.feed_entry['published_parsed']
        self.id = self.feed_entry['id']
