#!/usr/bin/env python3

import logging
import multiprocessing
import os
import pathlib
import random
import sys
import xml.etree.ElementTree as ElementTree
from typing import Optional

import click
from tqdm import tqdm

import podcastdownloader
import podcastdownloader.episode as episode
import podcastdownloader.writer as writer
from podcastdownloader.exceptions import EpisodeException, FeedException
from podcastdownloader.feed import Feed
from podcastdownloader.tagengine import writeTags

logger = logging.getLogger()


def _setup_logging(verbosity: int, logfile: Optional[str]):
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


def _load_feeds(feed_files: list[str], passed_feeds: list[str], opml_files: list[str]) -> list[Feed]:
    subscribed_feeds = []
    if feed_files:
        feed_files = [_check_required_path(file) for file in feed_files]
        for feed_file in feed_files:
            with open(pathlib.Path(feed_file), 'r') as feed:
                for line in feed.readlines():
                    if line != '\n' and not line.strip().startswith('#'):
                        parsed_line = line.split(' #')[0].strip()
                        subscribed_feeds.append(Feed(parsed_line))
                        logger.debug(f'Feed {line.strip()} added')
    if opml_files:
        opml_files = [_check_required_path(file) for file in opml_files]
        for opml_loc in opml_files:
            opml_tree = ElementTree.parse(pathlib.Path(opml_loc))
            for opml_feed in opml_tree.getroot().iter('outline'):
                subscribed_feeds.append(Feed(opml_feed.attrib['xmlUrl']))
                logger.debug(f'Feed {opml_feed.attrib["xmlUrl"]} added')

    if passed_feeds:
        for arg_feed in passed_feeds:
            subscribed_feeds.append(Feed(arg_feed))
            logger.debug(f'Feed {arg_feed} added')

    return subscribed_feeds


def _check_required_path(test_path: str) -> pathlib.Path:
    test_path = pathlib.Path(test_path).resolve()
    if not test_path.exists():
        raise Exception(f'File {test_path} does not exist')
    return test_path


def map_fill_episode(ep: episode.Episode, destination: pathlib.Path) -> episode.Episode:
    try:
        ep.parse_rss_entry()
        ep.calculate_file_path(destination)
        logger.log(9, f'Episode {ep.title} parsed')
    except EpisodeException as e:
        logger.error(f'{ep.title} in podcast {ep.podcast} failed: {e}')
    return ep


def map_verify_episode_download(ep: episode.Episode) -> episode.Episode:
    try:
        ep.verify_download_file()
    except KeyError:
        logger.error(f'Episode {ep.title} in podcast {ep.podcast} could not be checked')
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


def map_ready_feed(in_feed: Feed) -> Optional[Feed]:
    try:
        in_feed.fetch_rss()
        in_feed.extract_episodes(-1)
        logger.debug(f'Feed {in_feed.title} downloaded')
        in_feed.feed = None
    except (FeedException, KeyError) as e:
        logger.error(f'Feed {in_feed.url} could not be parsed: {e}')
        return None
    return in_feed


def common_setup(context: click.Context) -> multiprocessing.Pool:
    _setup_logging(context.params['verbose'], context.params['log'])
    context.params['destination'] = _check_required_path(context.params['destination'])

    context.ensure_object(dict)
    pool = multiprocessing.Pool(context.params['threads'])

    existing_files = scan_existing_files(context)

    subscribed_feeds = download_feeds(context, pool)
    random.shuffle(subscribed_feeds)

    for feed in tqdm(subscribed_feeds, disable=context.params['suppress_progress']):
        feed.make_directory(context.params['destination'])
        feed.feed_episodes = list(pool.starmap(
            map_fill_episode, [(ep, context.params['destination']) for ep in feed.feed_episodes]))
        for ep in feed.feed_episodes:
            if ep.status != episode.EpisodeStatus.BLANK and str(ep.path) in existing_files:
                ep.status = episode.EpisodeStatus.DOWNLOADED

    context.obj['feeds'] = subscribed_feeds
    return pool


def download_feeds(context: click.Context, pool: multiprocessing.Pool) -> list[Feed]:
    subscribed_feeds = _load_feeds(context.params['file'], context.params['feed'], context.params['opml'])
    logger.info(f'{len(subscribed_feeds)} feeds to be downloaded')
    subscribed_feeds = list(
        tqdm(pool.imap_unordered(
            map_ready_feed,
            subscribed_feeds),
            total=len(subscribed_feeds),
            disable=context.params['suppress_progress']))
    subscribed_feeds = list(filter(None, subscribed_feeds))
    return subscribed_feeds


def scan_existing_files(context: click.Context) -> list[str]:
    existing_files = []
    logger.info('Beginning scan of existing files')
    for (dirpath, dirnames, filenames) in os.walk(context.params['destination']):
        existing_files.extend([str(pathlib.PurePath(dirpath, filename)) for filename in filenames])
    return existing_files


def map_download_episode(ep: episode.Episode):
    try:
        ep.download_content()
        logger.debug(f'Episode {ep.title} downloaded from podcast {ep.podcast}')
        try:
            writeTags(ep)
        except episode.EpisodeException as e:
            logger.warning(f'Tags could not be written to {ep.title} in podcast {ep.podcast}: {e}')
    except episode.EpisodeException as e:
        logger.error(f'{ep.title} failed to download: {e}')


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
def download(context: click.Context, **_):
    """Download episodes of supplied feeds to disk"""
    pool = common_setup(context)

    podcastdownloader.episode.max_attempts = context.params['max_attempts']

    for feed in context.obj['feeds']:
        writer.write_episode_playlist(feed, context.params['write_list'])

    episode_queue = bulk_check_episodes(context)

    # randomise the list, if all the episodes from one server are close together, then the server will start cutting off
    # downloads. this should limit/prevent that as much as possible to keep the average speed high
    random.shuffle(episode_queue)

    list(tqdm(pool.imap_unordered(
        map_download_episode,
        episode_queue),
        total=len(episode_queue),
        disable=context.params['suppress_progress']))
    _kill_pool(pool)


def bulk_check_episodes(context: click.Context) -> list[episode.Episode]:
    episode_queue = [episode for feed in context.obj['feeds'] for episode in feed.feed_episodes]
    episode_queue = list(filter(lambda e: e.status == podcastdownloader.episode.EpisodeStatus.PENDING, episode_queue))
    if context.params['max_downloads'] > 0:
        logger.info(f'Reducing number of downloads to a maximum of {context.params["max_downloads"]}')
        episode_queue = episode_queue[:context.params['max_downloads']]
    return episode_queue


@cli.command()
@add_common_options
@click.pass_context
def verify(context: click.Context, **_):
    """Verify all downloaded files"""
    pool = common_setup(context)

    episode_queue = [episode for feed in context.obj['feeds'] for episode in feed.feed_episodes]
    episode_queue = list(filter(lambda e: e.status == podcastdownloader.episode.EpisodeStatus.DOWNLOADED, episode_queue))

    logger.info(f'Commencing offline cache verification for {len(episode_queue)} episodes')

    checked_episodes = list(tqdm(pool.imap_unordered(
        map_verify_episode_download,
        episode_queue),
        total=len(episode_queue),
        disable=context.params['suppress_progress']))

    with open('output.txt', 'w') as file:
        for ep in filter(lambda e: e.status == podcastdownloader.episode.EpisodeStatus.CORRUPTED, checked_episodes):
            logger.error(f'Episode {ep.title} in podcast {ep.podcast} has a mismatched filesize, presumed corrupted')
            file.write(str(ep.path) + '\n')
    _kill_pool(pool)


@cli.command()
@add_common_options
@click.pass_context
def tag(context: click.Context, **_):
    """Update tags on downloaded files"""
    pool = common_setup(context)

    episode_queue = [episode for feed in context.obj['feeds'] for episode in feed.feed_episodes]
    episode_queue = list(filter(lambda e: e.status == podcastdownloader.episode.EpisodeStatus.DOWNLOADED, episode_queue))
    logger.info(f'Writing tags to {len(episode_queue)} files')

    list(tqdm(pool.imap_unordered(
        writeTags,
        episode_queue),
        total=len(episode_queue),
        disable=context.params['suppress_progress']))
    _kill_pool(pool)


def _kill_pool(pool: multiprocessing.Pool):
    pool.close()
    pool.join()


if __name__ == "__main__":
    cli()
