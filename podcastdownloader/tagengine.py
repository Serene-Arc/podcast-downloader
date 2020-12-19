#!/usr/bin/env python3

import logging
from datetime import datetime
from time import mktime

import mutagen
import mutagen.id3
import mutagen.mp3
import mutagen.mp4

from podcastdownloader.episode import Episode

logger = logging.getLogger(__name__)


def writeTags(episode: Episode):
    if episode.file_type is None:
        episode = _guess_file_type(episode)

    if episode.file_type in ('audio/mpeg', 'audio/mp3'):
        _write_id3_tags(episode)
    elif episode.file_type in ('audio/mp4', 'audio/x-m4a'):
        _write_mp4_tags(episode)


def _guess_file_type(episode: Episode) -> Episode:
    if str(episode.path).endswith('mp3'):
        episode.file_type = 'audio/mp3'
    return episode


def _write_id3_tags(episode: Episode):
    episode_tags = mutagen.id3.ID3FileType(episode.path, ID3=mutagen.id3.ID3)

    try:
        episode_tags.add_tags()
    except mutagen.MutagenError:
        pass

    episode_tags.tags.update_to_v24()
    tags = [
        ('TIT2', mutagen.id3.TIT2(encoding=3, text=episode.title)),
        ('TALB', mutagen.id3.TALB(encoding=3, text=episode.podcast)),
        ('TDOR', mutagen.id3.TDOR(encoding=3, text=datetime.fromtimestamp(
            mktime(episode.feed_entry['published_parsed'])).isoformat()))]

    if 'summary' in episode.feed_entry:
        tags.append(('TDES', mutagen.id3.TDES(encoding=3, text=episode.feed_entry['summary'])))
    elif 'subtitle' in episode.feed_entry:
        tags.append(('TDES', mutagen.id3.TDES(encoding=3, text=episode.feed_entry['subtitle'])))
    else:
        logger.debug(
            'Could not add description tag for episode {} in podcast {}'.format(
                episode.title, episode.podcast))

    if 'itunes_episode' in episode.feed_entry:
        tags.append(('TRCK', mutagen.id3.TRCK(encoding=3, text=episode.feed_entry['itunes_episode'])))
    else:
        logger.debug(
            'Could not add track number tag to episode {} in podcast {}'.format(
                episode.title, episode.podcast))

    for (tag, content) in tags:
        try:
            episode_tags[tag] = content
            logger.debug('Wrote tag {}'.format(tag))
        except Exception as e:
            logger.error('Mutagen had an error writing ID3 tag {}: {}'.format(tag, e))

    episode_tags.save(episode.path)


def _write_mp4_tags(episode: Episode):
    try:
        episode_tags = mutagen.mp4.MP4(episode.path)
    except mutagen.mp4.MP4StreamInfoError:
        logger.error('Thought {} was an MP4 file but it was not'.format(episode.path.name))
        return

    try:
        episode_tags.add_tags()
    except mutagen.MutagenError:
        pass

    tags = [(r'\xa9nam', episode.title),
            (r'\xa9alb', episode.podcast),
            (r'\xa9day', datetime.fromtimestamp(
                mktime(episode.feed_entry['published_parsed'])).isoformat())]

    if 'summary' in episode.feed_entry:
        tags.append((r'desc', episode.feed_entry['summary']))
    elif 'subtitle' in episode.feed_entry:
        tags.append((r'desc', episode.feed_entry['subtitle']))
    else:
        logger.debug(
            'Could not add description tag for episode {} in podcast {}'.format(
                episode.title, episode.podcast))

    if 'itunes_episode' in episode.feed_entry:
        tags.append((r'trkn', (int(episode.feed_entry['itunes_episode']), 0)))
    else:
        logger.debug(
            'Could not add track number tag to episode {} in podcast {}'.format(
                episode.title, episode.podcast))

    for (tag, content) in tags:
        try:
            episode_tags[tag] = content
        except Exception as e:
            logger.error(
                'Could not write tag {} with value {} to episode {} in podcast {}: {}'.format(
                    tag, content, episode.title, episode.podcast, e))

    episode_tags.save(episode.path)
