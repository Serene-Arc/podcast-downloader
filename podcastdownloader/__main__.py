#!/bin/usr/env python3

import configparser
import argparse
import xml.etree.ElementTree as et
import pathlib
from tqdm import tqdm
from feed import Feed
from episode import Episode, Status, PodcastException
from stageprint import setstage, print, input
import multiprocessing
import logging
import os
import random

parser = argparse.ArgumentParser()
logger = logging.getLogger(__name__)
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    filename='podcastdownloader.log',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.DEBUG)
logging.getLogger(__name__).setLevel(logging.DEBUG)


if __name__ == "__main__":
    parser.add_argument('-d', '--destination', help='directory to store downloads')
    parser.add_argument('-f', '--feed', action='append', help='feed to download')
    parser.add_argument('--file', action='append', help='location of a file of feeds')
    # parser.add_argument('-t', '--threads', type=int, default=3, help='number of concurrent downloads')
    parser.add_argument('-o', '--opml', help='location of an OPML file to load')
    # parser.add_argument('-s', '--split-podcasts', action='store_true',
    #                     help='flag to split the podcasts into different directories')
    # parser.add_argument('-n', '--number', type=int, default=-1, help='number of episodes to download')

    args = parser.parse_args()
    setstage('Loading')
    feeds = []

    if args.opml:
        opml_file = pathlib.Path(args.opml)
        opml_tree = et.parse(opml_file)
        logger.info('Loading OPML file')
        for opml_feed in opml_tree.getroot().iter('outline'):
            feeds.append(Feed(opml_feed.attrib['xmlUrl']))
            print('Feed {} added'.format(opml_feed.attrib['xmlUrl']))
            logging.debug('Feed {} added'.format(opml_feed.attrib['xmlUrl']))

    if args.feed:
        for arg_feed in args.feed:
            feeds.append(Feed(arg_feed))
            logging.debug('Feed {} added'.format(arg_feed))
            print('Feed {} added'.format(arg_feed))

    if args.file:
        for feed_file in args.file:
            with open(pathlib.Path(feed_file), 'r') as file:
                for line in file.readlines():
                    feeds.append(Feed(line.strip()))
                    print('Feed {} added'.format(line.strip()))

    episode_queue = []
    existingFiles = []

    print('Scanning existing files...')
    for (dirpath, dirnames, filenames) in os.walk(args.destination):
        existingFiles.extend([str(pathlib.PurePath(dirpath, filename)) for filename in filenames])

    def parseFeed(in_feed):
        in_feed.getFeed()
        return in_feed

    def fillEpisode(ep):
        try:
            ep.parseFeed()
            ep.calcPath(args.destination)

            if str(ep.path) in existingFiles:
                ep.status = Status.downloaded

            if ep.status == Status.pending:
                ep.download()
                try:
                    ep.writeTags()
                except PodcastException as e:
                    print('Tags could not be written to {} in podcast {}: {}'.format(ep.title, ep.podcast, e))
        except PodcastException as e:
            print('{} in podcast {} failed: {}'.format(ep.title, ep.podcast, e))

    pool = multiprocessing.Pool(10)

    # randomise the feed list, just so there's less chance of a slow group
    random.shuffle(feeds)

    setstage('Updating')
    print('Updating feeds...')
    feeds = list(tqdm(pool.imap_unordered(parseFeed, feeds), total=len(feeds)))

    episode_queue = [ep for feed in feeds for ep in feed.feed_episodes]
    print('{} episodes found'.format(len(episode_queue)))

    for feed in feeds:
        dest = pathlib.Path(args.destination, feed.title)
        if os.path.exists(dest) is False:
            logging.debug('Creating folder {}'.format(dest))
            os.mkdir(pathlib.Path(args.destination, feed.title))

    # randomise the list, if all the episodes from one server are close
    # together, then the server will start cutting off downloads. this should
    # limit/prevent that as much as possible to keep the average speed high
    random.shuffle(episode_queue)

    setstage('Downloading')
    list(tqdm(pool.imap_unordered(fillEpisode, episode_queue), total=len(episode_queue)))

    pool.close()
    pool.join()
    setstage('End')
    print('Program complete!')
