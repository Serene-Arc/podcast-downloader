#!/usr/bin/env python3

import argparse
from cgi import test
import configparser
import logging
import multiprocessing
import os
import pathlib
import random
import sys
import xml.etree.ElementTree as et

import click
from tqdm import tqdm

import podcastdownloader.episode as episode
import podcastdownloader.writer as writer
from podcastdownloader.exceptions import EpisodeException, FeedException
from podcastdownloader.feed import Feed
from podcastdownloader.tagengine import writeTags

logger = logging.getLogger()
pool = None


def _setup_logging(verbosity: int, logfile: str) -> None:
    logger.setLevel(1)
    stream_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('[%(asctime)s - %(name)s - %(levelname)s] - %(message)s')
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    logging.getLogger('urllib3').setLevel(logging.CRITICAL)

    if logfile:
        file_handler = logging.FileHandler(logfile)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)

    if verbosity == 0:
        stream_handler.setLevel(logging.INFO)
    elif verbosity == 1:
        stream_handler.setLevel(logging.DEBUG)
    elif verbosity >= 2:
        stream_handler.setLevel(9)


def _load_feeds(feed_files: list[str], passed_feeds: list[str], opml_files: list[str]) -> list[str]:
    if feed_files:
        feed_files = [_check_path(file) for file in feed_files]
    if opml_files:
        opml_files = [_check_path(file) for file in opml_files]

    subscribedFeeds = []

    if opml_files:
        for opml_loc in opml_files:
            opml_tree = et.parse(pathlib.Path(opml_loc))
            for opml_feed in opml_tree.getroot().iter('outline'):
                subscribedFeeds.append(Feed(opml_feed.attrib['xmlUrl']))
                logger.debug('Feed {} added'.format(opml_feed.attrib['xmlUrl']))
    if passed_feeds:
        for arg_feed in passed_feeds:
            subscribedFeeds.append(Feed(arg_feed))
            logger.debug('Feed {} added'.format(arg_feed))
    if feed_files:
        for feed_file in feed_files:
            with open(pathlib.Path(feed_file), 'r') as feed:
                for line in feed.readlines():
                    if line != '\n' and not line.strip().startswith('#'):
                        parsed_line = line.split(' #')[0].strip()
                        subscribedFeeds.append(Feed(parsed_line))
                        logger.debug('Feed {} added'.format(line.strip()))

    return subscribedFeeds


def _check_path(test_path: str) -> pathlib.Path:
    test_path = pathlib.Path(test_path).resolve()
    if not test_path.exists():
        raise Exception('File {} does not exist'.format(str(test_path)))
    return test_path


def fillEpisode(ep: episode.Episode, destination: str) -> episode.Episode:
    try:
        ep.parseRSSEntry()
        ep.calcPath(destination)
        logger.log(9, 'Episode {} parsed'.format(ep.title))
    except EpisodeException as e:
        logger.error('{} in podcast {} failed: {}'.format(ep.title, ep.podcast, e))
    return ep


def check_episode(ep: episode.Episode) -> episode.Episode:
    try:
        ep.verifyDownload()
    except KeyError:
        logger.error('Episode {} in podcast {} could not be checked'.format(ep.title, ep.podcast))
    return ep


_common_options = [
    click.argument('destination'),
    click.option('--file', multiple=True, default=[]),
    click.option('--log'),
    click.option('--suppress-progress', default=False, is_flag=True),
    click.option('-f', '--feed', multiple=True, default=[]),
    click.option('-o', '--opml', multiple=True, default=[]),
    click.option('-t', '--threads', type=int, default=10),
    click.option('-v', '--verbose', count=True, default=0)
]


def add_common_options(func):
    for option in reversed(_common_options):
        func = option(func)
    return func


def readyFeed(in_feed: Feed) -> Feed:
    try:
        in_feed.fetchRSS()
        in_feed.extractEpisodes(-1)
        logger.debug('Feed {} downloaded'.format(in_feed.title))
        in_feed.feed = None
    except (FeedException, KeyError) as e:
        logger.error('Feed {} could not be parsed: {}'.format(in_feed.url, e))
        return None
    return in_feed


def common_setup(context: click.Context):
    _setup_logging(context.params['verbose'], context.params['log'])
    context.params['destination'] = _check_path(context.params['destination'])

    context.ensure_object(dict)

    global pool
    pool = multiprocessing.Pool(context.params['threads'])

    subscribedFeeds = _load_feeds(context.params['file'], context.params['feed'], context.params['opml'])
    logger.info('{} feeds to be downloaded'.format(len(subscribedFeeds)))

    episode_queue = []
    existingFiles = []

    logger.info('Beginning scan of existing files')
    for (dirpath, dirnames, filenames) in os.walk(context.params['destination']):
        existingFiles.extend([str(pathlib.PurePath(dirpath, filename)) for filename in filenames])

    random.shuffle(subscribedFeeds)

    logger.info('Updating feeds...')

    subscribedFeeds = list(
        tqdm(pool.imap_unordered(
            readyFeed,
            subscribedFeeds),
            total=len(subscribedFeeds),
            disable=context.params['suppress_progress']))
    subscribedFeeds = list(filter(None, subscribedFeeds))

    for feed in tqdm(subscribedFeeds, disable=context.params['suppress_progress']):
        feed.makeDirectory(context.params['destination'])
        feed.feed_episodes = list(
            pool.starmap(
                fillEpisode, [
                    (ep, context.params['destination']) for ep in feed.feed_episodes]))
        for ep in feed.feed_episodes:
            if str(ep.path) in existingFiles:
                ep.status = episode.Status.downloaded

    context.obj['feeds'] = subscribedFeeds


@click.group()
def cli():
    pass


@cli.command()
@add_common_options
@click.option('--max-attempts', type=int, default=10)
@click.option('-l', '--limit', type=int, default=-1)
@click.option('-m', '--max-downloads', type=int, default=-1)
@click.option('-w', '--write-list', multiple=True,
              type=click.Choice(['none', 'audacious', 'text', 'm3u']), default=['none'])
@click.pass_context
def download(context: click.Context, **kwargs):
    """Download episodes of supplied feeds to disk"""
    common_setup(context)

    episode.max_attempts = context.params['max_attempts']

    def downloadEpisode(ep: episode.Episode):
        try:
            ep.downloadContent()
            logger.debug('Episode {} downloaded from podcast {}'.format(ep.title, ep.podcast))
            try:
                writeTags(ep)
            except episode.EpisodeException as e:
                logger.warning('Tags could not be written to {} in podcast {}: {}'.format(ep.title, ep.podcast, e))
        except episode.EpisodeException as e:
            logger.error('{} failed to download: {}'.format(ep.title, e))

    for feed in context.obj['feeds']:
        writer.writeEpisode(feed, context.params['write_list'])

    episode_queue = [episode for feed in context.obj['feeds'] for episode in feed.feed_episodes]
    episode_queue = list(filter(lambda e: e.status == episode.Status.pending, episode_queue))
    if context.params['max_downloads'] > 0:
        logger.info('Reducing number of downloads to a maximum of {}'.format(context.params['max_downloads']))
        episode_queue = episode_queue[:context.params['max_downloads']]

    # randomise the list, if all the episodes from one server are close
    # together, then the server will start cutting off downloads. this should
    # limit/prevent that as much as possible to keep the average speed high
    random.shuffle(episode_queue)

    list(tqdm(pool.imap_unordered(
        downloadEpisode,
        episode_queue),
        total=len(episode_queue),
        disable=context.params['suppress_progress']))


@cli.command()
@add_common_options
@click.pass_context
def verify(context: click.Context, **kwargs):
    """Verify all downloaded files"""
    common_setup(context)

    episode_queue = [episode for feed in context.obj['feeds'] for episode in feed.feed_episodes]
    episode_queue = list(filter(lambda e: e.status == episode.Status.downloaded, episode_queue))

    logger.info('Commencing offline cache verification for {} episodes'.format(len(episode_queue)))

    checked_episodes = list(
        tqdm(pool.imap_unordered(
            check_episode,
            episode_queue),
            total=len(episode_queue),
            disable=context.params['suppress_progress']))

    with open('output.txt', 'w') as file:
        for ep in filter(lambda e: e.status == episode.Status.corrupted, checked_episodes):
            logger.error(
                'Episode {} in podcast {} has a mismatched filesize, presumed corrupted'.format(
                    ep.title, ep.podcast))
            file.write(str(ep.path) + '\n')


@cli.command()
@add_common_options
@click.pass_context
def tag(context: click.Context, **kwargs):
    """Update tags on downloaded files"""
    common_setup(context)

    episode_queue = [episode for feed in context.obj['feeds'] for episode in feed.feed_episodes]
    episode_queue = list(filter(lambda e: e.status == episode.Status.downloaded, episode_queue))
    logger.info('Writing tags to {} files'.format(len(episode_queue)))

    checked_episodes = list(
        tqdm(pool.imap_unordered(
            writeTags,
            episode_queue),
            total=len(episode_queue),
            disable=context.params['suppress_progress']))


if __name__ == "__main__":
    cli()
    pool.close()
    pool.join()
