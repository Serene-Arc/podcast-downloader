#!/bin/usr/env python3

import configparser
import argparse
import xml.etree.ElementTree as et
import pathlib
from tqdm import tqdm
from feed import Feed
from episode import Episode, Status
from stageprint import setstage, print, input
import multiprocessing
import logging
import os

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
    # parser.add_argument('-t', '--threads', type=int, default=3, help='number of concurrent downloads')
    parser.add_argument('-o', '--opml', help='location of an OPML file to load')
    # parser.add_argument('-s', '--split-podcasts', action='store_true',
    #                     help='flag to split the podcasts into different directories')
    # parser.add_argument('-n', '--number', type=int, default=-1, help='number of episodes to download')

    args = parser.parse_args()
    setstage('Loading')
    feeds = []

    if args.opml:
        feed_file = pathlib.Path(args.opml)
        feed_tree = et.parse(feed_file)
        logger.info('Loading OPML file')
        for found_feed in feed_tree.getroot().iter('outline'):
            feeds.append(Feed(found_feed.attrib['xmlUrl']))
            print('Feed {} added'.format(found_feed.attrib['xmlUrl']))
            logging.debug('Feed {} added'.format(found_feed.attrib['xmlUrl']))

    if args.feed:
        for arg_feed in args.feed:
            feeds.append(Feed(arg_feed))
            logging.debug('Feed {} added'.format(arg_feed))
            print('Feed {} added'.format(arg_feed))

    setstage('Updating')
    print('Updating feeds...')

    for feed in tqdm(feeds):
        feed.getFeed()
        feed.fillEpisodes()
        print('{} episodes found'.format(sum([len(feed.feed_episodes) for feed in feeds])))

    download_queue = multiprocessing.JoinableQueue()

    for feed in feeds:
        dest = pathlib.Path(args.destination, feed.title)
        if os.path.exists(dest) is False:
            logging.debug('Creating folder {}'.format(dest))
            os.mkdir(pathlib.Path(args.destination, feed.title))

        for ep in feed.feed_episodes:
            ep.calcPath(args.destination)
            ep.checkExistence()

        for episode in filter(lambda ep: ep.status != Status.downloaded, feed.feed_episodes):
            download_queue.put(episode)

    while download_queue.empty() is False:
        ep.download()
        print()
