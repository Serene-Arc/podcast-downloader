#!/usr/bin/env python3


class PodcastException(Exception):
    pass


class FeedException(PodcastException):
    pass


class EpisodeException(PodcastException):
    pass
