#!/usr/bin/env python3
# coding=utf-8

class PodcastException(Exception):
    pass


class FeedException(PodcastException):
    pass


class EpisodeException(PodcastException):
    pass
