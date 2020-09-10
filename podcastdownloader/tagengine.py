#!/usr/bin/env python3

import logging
import pathlib
from datetime import datetime
from time import mktime

import mutagen
import mutagen.id3
import mutagen.mp3
import mutagen.mp4

from podcastdownloader.episode import Episode

logger = logging.getLogger(__name__)


def writeTags(episode: Episode):

    try:
        if episode.file_type is None:
            episode = _guessFileType(episode)
    except AttributeError:
        episode = _guessFileType(episode)

    if episode.file_type in ('audio/mpeg', 'audio/mp3'):
        _writeID3Tags(episode)
    elif episode.file_type in ('audio/mp4', 'audio/x-m4a'):
        _writeMP4Tags(episode)


def _guessFileType(episode: Episode):
    if str(episode.path).endswith('mp3'):
        episode.file_type = 'audio/mp3'
    return episode


def _writeID3Tags(episode: Episode):
    episode_tags = mutagen.id3.ID3FileType(episode.path, ID3=mutagen.id3.ID3)

    try:
        episode_tags.add_tags()
    except mutagen.MutagenError:
        pass

    episode_tags.tags.update_to_v24()
    tags = [
        ('TIT2', mutagen.id3.TIT2(encoding=3, text=episode.title)),
        ('TALB', mutagen.id3.TALB(encoding=3, text=episode.podcast)),
        ('TDES', mutagen.id3.TDES(encoding=3, text=episode.feed_entry['summary'])),
        ('TDOR', mutagen.id3.TDOR(encoding=3, text=datetime.fromtimestamp(
            mktime(episode.feed_entry['published_parsed'])).isoformat()))]

    try:
        tags.append(('TRCK', mutagen.id3.TRCK(encoding=3, text=episode.feed_entry['itunes_episode'])))
    except KeyError:
        logger.warning('Track number could not be written to file {}'.format(episode.path))

    for (tag, content) in tags:
        try:
            episode_tags[tag] = content
            logger.debug('Wrote tag {}'.format(tag))
        except Exception as e:
            logger.error('Mutagen had an error writing ID3 tag {}: {}'.format(tag, e))

    episode_tags.save(episode.path)


def _writeMP4Tags(episode: Episode):
    logger.critical('Not yet implemented')
