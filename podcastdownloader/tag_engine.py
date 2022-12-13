#!/usr/bin/env python3
# coding=utf-8

import logging

import mutagen
import mutagen.id3
import mutagen.mp3
import mutagen.mp4
from mutagen.id3 import PCST, TALB, TDES, TIT2

from podcastdownloader.episode import Episode
from podcastdownloader.exceptions import TagEngineError

logger = logging.getLogger(__name__)


class TagEngine:
    def __init__(self):
        pass

    @staticmethod
    def tag_episode(episode: Episode):
        tag_file = mutagen.File(episode.file_path)
        if tag_file is None:
            raise TagEngineError(f"Could not write tags to {episode.title} in {episode.podcast_name}")
        try:
            tag_file.add_tags()
        except mutagen.MutagenError:
            pass
        if isinstance(tag_file.tags, mutagen.id3.ID3):
            TagEngine._write_id3_tags(episode, tag_file)
        elif isinstance(tag_file.tags, mutagen.mp4.MP4Tags):
            TagEngine._write_mp4_tags(episode, tag_file)
        else:
            raise TagEngineError(f"Tagging for type {type(tag_file).__name__} not supported")

    @staticmethod
    def _write_id3_tags(episode: Episode, tag_file: mutagen.File):
        tag_file.tags.add(PCST(value=True))  # Podcast Flag
        tag_file.tags.add(TALB(encoding=3, text=episode.podcast_name))
        tag_file.tags.add(TDES(encoding=3, text=episode.feed.get("summary", "")))
        tag_file.tags.add(TIT2(encoding=3, text=episode.title))
        tag_file.save()

    @staticmethod
    def _write_mp4_tags(episode: Episode, tag_file: mutagen.File):
        tag_file.tags["\xa9nam"] = episode.title  # Episode title
        tag_file.tags["\xa9alb"] = episode.podcast_name  # Podcast name
        tag_file.tags["pcst"] = True  # Podcast bit
        tag_file.tags["desc"] = episode.feed.get("summary", "")
        tag_file.save()
