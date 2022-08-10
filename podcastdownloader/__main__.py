#!/usr/bin/env python3

import asyncio
import itertools
import logging
import random
import sys
from asyncio.queues import Queue
from pathlib import Path
from typing import Optional

import aiohttp
import click

import podcastdownloader.utility_functions as util
from podcastdownloader.exceptions import EpisodeException, PodcastException
from podcastdownloader.podcast import Podcast
from podcastdownloader.writer import write_episode_playlist
from http.cookiejar import MozillaCookieJar

logger = logging.getLogger()


def _setup_logging(verbosity: int):
    logger.setLevel(1)
    stream = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter('[%(asctime)s - %(name)s - %(levelname)s] - %(message)s')
    stream.setFormatter(formatter)
    logger.addHandler(stream)
    if verbosity >= 1:
        stream.setLevel(logging.DEBUG)
    else:
        stream.setLevel(logging.INFO)
    logging.getLogger('asyncio').setLevel(logging.CRITICAL)
    logging.getLogger('chardet').setLevel(logging.CRITICAL)


_common_options = [
    click.argument('destination', type=str),
    click.option('-v', '--verbose', type=int, default=0, count=True),
    click.option('-f', '--feed', type=str, multiple=True, default=[]),
    click.option('-F', '--file', type=str, multiple=True, default=[]),
    click.option('--opml', type=str, multiple=True, default=[]),
]


async def fill_individual_feed(in_queue: Queue, out_queue: Queue, destination: Path, session: aiohttp.ClientSession):
    while not in_queue.empty():
        podcast = await in_queue.get()
        if podcast is None:
            break
        logger.debug(f'Beginning retrieval for {podcast.url}')
        try:
            await podcast.download_feed(session)
            for episode in podcast.episodes:
                try:
                    await episode.calculate_path(destination, session)
                except TypeError:
                    logger.error(f'Failed to parse {episode.title} in {episode.podcast_name}')
        except PodcastException as e:
            logger.error(e)
        except Exception:
            logger.critical(f'Error with {podcast.url}')
            raise
        else:
            await out_queue.put(podcast)
            logger.info(f'Retrieved RSS for {podcast.name}')
        in_queue.task_done()


async def download_individual_episode(in_queue: Queue, session: aiohttp.ClientSession):
    while not in_queue.empty():
        episode = await in_queue.get()
        if episode is None:
            break
        logger.debug(f'Attempting download of episode {episode.title} in {episode.podcast_name}')
        try:
            await episode.download(session)
        except EpisodeException as e:
            logger.error(e)
        in_queue.task_done()


def add_common_options(func):
    for option in _common_options:
        func = option(func)
    return func


@click.group()
def cli():
    pass


@cli.command('download')
@add_common_options
@click.option('-l', '--limit', type=int, default=None)
@click.option('-t', '--threads', type=int, default=10)
@click.option('-w', '--write-playlist', type=click.Choice(('m3u',)), default=(), multiple=True)
def cli_download(
        destination: str,
        feed: tuple[str],
        file: tuple[str],
        limit: Optional[int],
        opml: tuple[str],
        threads: int,
        verbose: int,
        write_playlist: tuple[str],
):
    _setup_logging(verbose)
    destination = Path(destination).expanduser().resolve()
    if not destination.exists():
        logger.warning(f'Specified destination {destination} does not exist, creating it now')
        destination.mkdir(parents=True)

    all_feeds = set(itertools.chain(feed, util.load_feeds_from_text_file(file), util.load_feeds_from_opml(opml)))
    logger.info(f'{len(all_feeds)} feeds found')
    if all_feeds:
        asyncio.run(download_episodes(all_feeds, destination, threads, write_playlist, limit))
    else:
        logger.error('No feeds have been provided')
    logger.info('Program Complete')


async def download_episodes(
    all_feeds: set[str],
    destination: Path,
    threads: int,
    playlist_formats: tuple[str],
    limit: Optional[int],
):
    unfilled_podcasts = Queue()
    filled_podcasts = Queue()
    episodes = Queue()
    for url in all_feeds:
        await unfilled_podcasts.put(Podcast(url))

    async with aiohttp.ClientSession(
            headers={
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:103.0) Gecko/20100101 Firefox/103.0',
            },
    ) as session:
        feed_fillers = [asyncio.create_task(
            fill_individual_feed(unfilled_podcasts, filled_podcasts, destination, session)
        ) for _ in range(1, threads)]
        await asyncio.gather(*feed_fillers)
        await unfilled_podcasts.join()
        logger.info('All feeds filled')

        podcasts = []
        while not filled_podcasts.empty():
            podcast = filled_podcasts.get_nowait()
            write_episode_playlist(podcast, playlist_formats)
            podcasts.append(podcast)

        if limit:
            logger.info(f'Limiting episodes per podcast to {limit} entries')
            for podcast in podcasts:
                podcast.episodes = podcast.episodes[:limit]

        unfilled_episodes = list(filter(
            lambda e: not e.file_path or not e.file_path.exists(),
            [ep for pod in podcasts for ep in pod.episodes],
        ))
        logger.info(f'{len(unfilled_episodes)} episodes to download')

        random.shuffle(unfilled_episodes)

        for ep in unfilled_episodes:
            await episodes.put(ep)

        episode_downloaders = [asyncio.create_task(
            download_individual_episode(episodes, session)
        ) for _ in range(1, threads)]

        await asyncio.gather(*episode_downloaders)
        await episodes.join()


if __name__ == '__main__':
    cli()
