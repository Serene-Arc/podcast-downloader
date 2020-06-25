#!/bin/usr/env python3

import configparser
import argparse
import xml.etree.ElementTree as et
import pathlib
from tqdm import tqdm
from podcastdownloader.feed import Feed
from podcastdownloader.episode import Episode, Status, PodcastException, max_attempts
import multiprocessing
import os
import random
import podcastdownloader.writer
import logging
import sys

parser = argparse.ArgumentParser()


if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    stream = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('[%(asctime)s - %(levelname)s] - %(message)s')
    stream.setFormatter(formatter)
    logger.addHandler(stream)

    parser.add_argument('destination', help='directory to store downloads')
    parser.add_argument('-f', '--feed', action='append', help='feed to download')
    parser.add_argument('--file', action='append', help='location of a file of feeds')
    parser.add_argument('-o', '--opml', action='append', help='location of an OPML file to load')
    parser.add_argument('-t', '--threads', type=int, default=10, help='number of concurrent downloads')
    parser.add_argument('-l', '--limit', type=int, default=-1, help='number of episodes to download from each feed')
    parser.add_argument(
        '-w',
        '--write-list',
        choices=[
            'none',
            'audacious',
            'text'],
        default='none',
        help='flag to write episode list')
    parser.add_argument('-s', '--suppress-progress', action='store_true')
    parser.add_argument('-v', '--verbose', action='count', default=0, help='increase the verbosity')
    parser.add_argument('--max-attempts', type=int, help='maximum nuimber of attempts to download file')

    args = parser.parse_args()
    if args.file:
        args.file = [pathlib.Path(file).resolve() for file in args.file]
    if args.opml:
        args.opml = [pathlib.Path(file).resolve() for file in args.opml]
    args.destination = pathlib.Path(args.destination).resolve()

    if args.verbose == 0:
        logger.setLevel(logging.INFO)
    elif args.verbose >= 1:
        logger.setLevel(logging.DEBUG)

    if args.max_attempts:
        max_attempts = args.max_attempts

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
                    subscribedFeeds.append(Feed(line.strip()))
                    logger.debug('Feed {} added'.format(line.strip()))

    episode_queue = []
    existingFiles = []

    logger.info('{} feeds to be downloaded'.format(len(subscribedFeeds)))

    logger.info('Scanning existing files...')
    for (dirpath, dirnames, filenames) in os.walk(args.destination):
        existingFiles.extend([str(pathlib.PurePath(dirpath, filename)) for filename in filenames])

    def readyFeed(in_feed):
        try:
            in_feed.parseRSS(args.limit, args.destination, args.write_list)
        except KeyError as e:
            logger.error('Feed {} could not be parsed: {}'.format(in_feed.url, e))
            return None
        return in_feed

    def fillEpisode(ep):
        try:
            ep.parseRSSEntry()
            ep.calcPath(args.destination)

            if str(ep.path) in existingFiles:
                ep.status = Status.downloaded
        except PodcastException as e:
            logger.error('{} in podcast {} failed: {}'.format(ep.title, ep.podcast, e))
        return ep

    def downloadEpisode(ep):
        try:
            ep.downloadContent()
        except PodcastException as e:
            logger.error('{} failed to download: {}'.format(ep.title, e))

        try:
            ep.writeTags()
        except PodcastException as e:
            logger.warning('Tags could not be written to {} in podcast {}: {}'.format(ep.title, ep.podcast, e))

    pool = multiprocessing.Pool(args.threads)

    # randomise the feed list, just so there's less chance of a slow group
    random.shuffle(subscribedFeeds)

    logger.info('Updating feeds...')

    subscribedFeeds = list(
        tqdm(
            pool.imap_unordered(
                readyFeed,
                subscribedFeeds),
            total=len(subscribedFeeds),
            disable=args.suppress_progress))
    subscribedFeeds = list(filter(None, subscribedFeeds))

    logger.info('Parsing feeds...')

    for feed in tqdm(subscribedFeeds, disable=args.suppress_progress):
        feed.feed_episodes = list(pool.imap(fillEpisode, feed.feed_episodes))
        if args.write_list == 'audacious':
            writer.writeEpisodeAudacious(feed)
        elif args.write_list == 'text':
            writer.writeEpisodeText(feed)

        episode_queue.extend([ep for ep in feed.feed_episodes if ep.status == Status.pending])

    logger.info('{} episodes to download'.format(len(episode_queue)))

    # randomise the list, if all the episodes from one server are close
    # together, then the server will start cutting off downloads. this should
    # limit/prevent that as much as possible to keep the average speed high
    random.shuffle(episode_queue)

    list(
        tqdm(
            pool.imap_unordered(
                downloadEpisode,
                episode_queue),
            total=len(episode_queue),
            disable=args.suppress_progress))

    pool.close()
    pool.join()
