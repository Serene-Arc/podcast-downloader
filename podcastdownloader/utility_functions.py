#!/usr/bin/env python3
# coding=utf-8

import logging
import re
import xml.etree.ElementTree as ElementTree
from pathlib import Path
from typing import Optional

from podcastdownloader.exceptions import FeedException

logger = logging.getLogger(__name__)


def _check_required_path(file_path: str) -> Path:
    result = Path(file_path).resolve().expanduser()
    return result


def load_feeds_from_text_file(feed_files: list[str]) -> list[str]:
    result = []
    feed_files = [_check_required_path(file) for file in feed_files]
    for feed_file in feed_files:
        with open(Path(feed_file), 'r') as feed:
            for line in feed.readlines():
                if parsed_line := _clean_text_line(line):
                    result.append(parsed_line)
                    logger.debug(f'Feed {parsed_line} added')
    return result


def _clean_text_line(in_string: str) -> Optional[str]:
    non_feed_pattern = re.compile(r'^\s*(#.*)?$')
    if re.match(non_feed_pattern, in_string):
        return None
    feed_pattern = re.compile(r'^\s*(.*?)(\s+#.*)?$')
    feed_match = re.match(feed_pattern, in_string)
    if feed_match:
        return feed_match.group(1)
    else:
        raise FeedException(f'Could not extract feed from {in_string.strip()}')


def load_feeds_from_opml(opml_files: list[str]) -> list[str]:
    result = []
    opml_files = [_check_required_path(file) for file in opml_files]
    for opml_loc in opml_files:
        opml_tree = ElementTree.parse(Path(opml_loc))
        for opml_feed in opml_tree.getroot().iter('outline'):
            result.append(opml_feed.attrib['xmlUrl'])
            logger.debug(f'Feed {opml_feed.attrib["xmlUrl"]} added')
    return result
