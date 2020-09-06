#!/usr/bin/env python3

import argparse
import configparser
import logging
import multiprocessing
import os
import pathlib
import random
import sys
import xml.etree.ElementTree as et

from tqdm import tqdm

import podcastdownloader.episode as episode
import podcastdownloader.writer as writer
from podcastdownloader.exceptions import FeedException, EpisodeException
from podcastdownloader.feed import Feed

parser = argparse.ArgumentParser()


if __name__ == "__main__":

    parser.add_argument('destination', help='directory to store downloads')
    parser.add_argument('-f', '--feed', action='append', help='feed to download')
    parser.add_argument('--file', action='append', help='location of a file of feeds')
    parser.add_argument('-o', '--opml', action='append', help='location of an OPML file to load')
    parser.add_argument('-t', '--threads', type=int, default=10, help='number of concurrent downloads')
    parser.add_argument('-l', '--limit', type=int, default=-1, help='number of episodes to download from each feed')
    parser.add_argument(
        '-w', '--write-list',
        choices=['none', 'audacious', 'text'],
        default='none',
        help='flag to write episode list')
    parser.add_argument('-s', '--suppress-progress', action='store_true')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='increase the verbosity')
    parser.add_argument('--max-attempts', type=int, help='maximum nuimber of attempts to download file')
    download_alternates = parser.add_mutually_exclusive_group()
    download_alternates.add_argument('--skip-download', action='store_true', help='skips the download of episodes')
    download_alternates.add_argument('--verify', action='store_true', help='verify all downloaded files')
    parser.add_argument('-m', '--max-downloads', type=int, default=0,
                        help='maximum number of total episodes to download')
    parser.add_argument('--log', help='log to specified file')

    args = parser.parse_args()

    if args.file:
        args.file = [pathlib.Path(file).resolve() for file in args.file]
    if args.opml:
        args.opml = [pathlib.Path(file).resolve() for file in args.opml]
    args.destination = pathlib.Path(args.destination).resolve()

    logger = logging.getLogger()
    logger.setLevel(1)
    stream_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('[%(asctime)s - %(levelname)s] - %(message)s')
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    logging.getLogger('urllib3').setLevel(logging.CRITICAL)

    if args.log:
        file_handler = logging.FileHandler(args.log)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)

    if args.verbose == 0:
        stream_handler.setLevel(logging.INFO)
    elif args.verbose == 1:
        stream_handler.setLevel(logging.DEBUG)
    elif args.verbose >= 2:
        stream_handler.setLevel(9)

    if args.max_attempts:
        episode.max_attempts = args.max_attempts

    subscribedFeeds = []

    if args.opml:
        for opml_loc in args.opml:
            opml_tree = et.parse(pathlib.Path(opml_loc))
            for opml_feed in opml_tree.getroot().iter('outline'):
                subscribedFeeds.append(Feed(opml_feed.attrib['xmlUrl']))
                logger.debug('Feed {} added'.format(opml_feed.attrib['xmlUrl']))

    if args.feed:
        for arg_feed in args.feed:
            subscribedFeeds.append(Feed(arg_feed))
            logger.debug('Feed {} added'.format(arg_feed))

    if args.file:
        for feed_file in args.file:
            with open(pathlib.Path(feed_file), 'r') as file:
                for line in file.readlines():
                    if line != '\n' and not line.startswith('#'):
                        subscribedFeeds.append(Feed(line.strip()))
                        logger.debug('Feed {} added'.format(line.strip()))

    episode_queue = []
    existingFiles = []

    logger.info('{} feeds to be downloaded'.format(len(subscribedFeeds)))

    logger.info('Scanning existing files...')
    for (dirpath, dirnames, filenames) in os.walk(args.destination):
        existingFiles.extend([str(pathlib.PurePath(dirpath, filename)) for filename in filenames])

    def readyFeed(in_feed: Feed) -> Feed:
        try:
            logger.debug('Attempting to download feed {}'.format(in_feed.url))
            in_feed.fetchRSS()
            in_feed.extractEpisodes(args.limit)
            logger.debug('Feed {} downloaded'.format(in_feed.title))
            in_feed.feed = None

        except (FeedException, KeyError) as e:
            logger.error('Feed {} could not be parsed: {}'.format(in_feed.url, e))
            return None

        return in_feed

    def fillEpisode(ep: episode.Episode) -> episode.Episode:
        try:
            ep.parseRSSEntry()
            ep.calcPath(args.destination)
            logger.log(9, 'Episode {} parsed'.format(ep.title))

            if str(ep.path) in existingFiles:
                ep.status = episode.Status.downloaded

        except EpisodeException as e:
            logger.error('{} in podcast {} failed: {}'.format(ep.title, ep.podcast, e))
        return ep

    def downloadEpisode(ep: episode.Episode):
        try:
            ep.downloadContent()
            logger.debug('Episode {} downloaded'.format(ep.title))
            try:
                ep.writeTags()
            except episode.EpisodeException as e:
                logger.warning('Tags could not be written to {} in podcast {}: {}'.format(ep.title, ep.podcast, e))
        except episode.EpisodeException as e:
            logger.error('{} failed to download: {}'.format(ep.title, e))

    def check_episode(ep: episode.Episode) -> episode.Episode:
        try:
            ep.verifyDownload()
        except KeyError:
            logger.error('Episode {} in podcast {} could not be checked'.format(ep.title, ep.podcast))
        return ep

    pool = multiprocessing.Pool(args.threads)

    # randomise the feed list, just so there's less chance of a slow group
    random.shuffle(subscribedFeeds)

    logger.info('Updating feeds...')

    subscribedFeeds = list(
        tqdm(pool.imap_unordered(
            readyFeed,
            subscribedFeeds),
            total=len(subscribedFeeds),
            disable=args.suppress_progress))
    subscribedFeeds = list(filter(None, subscribedFeeds))

    logger.info('Parsing episodes...')

    for feed in tqdm(subscribedFeeds, disable=args.suppress_progress):
        feed.makeDirectory(args.destination)
        feed.feed_episodes = list(pool.imap(fillEpisode, feed.feed_episodes))
        writer.writeEpisode(feed, args.write_list)
        episode_queue.extend([ep for ep in feed.feed_episodes])

    logger.info('{} episodes missing from archive'.format(
        len(list(filter(lambda e: e.status == episode.Status.pending, episode_queue)))))
    if args.verify:
        episode_queue = list(filter(lambda e: e.status == episode.Status.downloaded, episode_queue))
        logger.info('Commencing offline cache verification')
        random.shuffle(episode_queue)

        checked_episodes = list(
            tqdm(pool.imap_unordered(
                check_episode,
                episode_queue),
                total=len(episode_queue),
                disable=args.suppress_progress))

        with open('output.txt', 'w') as file:
            for ep in filter(lambda e: e.status == episode.Status.corrupted, checked_episodes):
                logger.error(
                    'Episode {} in podcast {} has a mismatched filesize, presumed corrupted'.format(
                        ep.title, ep.podcast))
                file.write(str(ep.path) + '\n')

    elif args.skip_download:
        episode_queue = list(filter(lambda e: e.status == episode.Status.pending, episode_queue))
        for ep in episode_queue:
            logger.info('Skipping download for episode {} in podcast {}'.format(ep.title, ep.podcast))

    else:
        episode_queue = list(filter(lambda e: e.status == episode.Status.pending, episode_queue))
        if args.max_downloads > 0:
            logger.info('Reducing number of downloads to a maximum of {}'.format(args.max_downloads))
            episode_queue = episode_queue[:args.max_downloads]

        # randomise the list, if all the episodes from one server are close
        # together, then the server will start cutting off downloads. this should
        # limit/prevent that as much as possible to keep the average speed high
        random.shuffle(episode_queue)

        list(tqdm(pool.imap_unordered(
            downloadEpisode,
            episode_queue),
            total=len(episode_queue),
            disable=args.suppress_progress))

    pool.close()
    pool.join()
