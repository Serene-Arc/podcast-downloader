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
import os
import random

parser = argparse.ArgumentParser()


if __name__ == "__main__":
    parser.add_argument('destination', help='directory to store downloads')
    parser.add_argument('-f', '--feed', action='append', help='feed to download')
    parser.add_argument('--file', action='append', help='location of a file of feeds')
    parser.add_argument('-o', '--opml', action='append', help='location of an OPML file to load')
    parser.add_argument('-t', '--threads', type=int, default=10, help='number of concurrent downloads')
    parser.add_argument('-l', '--limit', type=int, default=-1, help='number of episodes to download from each feed')
    parser.add_argument('-w', '--write-list', action='store_true', help='flag to write episode list')

    args = parser.parse_args()
    setstage('Loading')
    subscribedFeeds = []

    if args.opml:
        for opml_loc in args.opml:
            opml_tree = et.parse(pathlib.Path(opml_loc))
            for opml_feed in opml_tree.getroot().iter('outline'):
                subscribedFeeds.append(Feed(opml_feed.attrib['xmlUrl']))
                print('Feed {} added'.format(opml_feed.attrib['xmlUrl']))

    if args.feed:
        for arg_feed in args.feed:
            subscribedFeeds.append(Feed(arg_feed))
            print('Feed {} added'.format(arg_feed))

    if args.file:
        for feed_file in args.file:
            with open(pathlib.Path(feed_file), 'r') as file:
                for line in file.readlines():
                    subscribedFeeds.append(Feed(line.strip()))
                    print('Feed {} added'.format(line.strip()))

    episode_queue = []
    existingFiles = []

    print('Scanning existing files...')
    for (dirpath, dirnames, filenames) in os.walk(args.destination):
        existingFiles.extend([str(pathlib.PurePath(dirpath, filename)) for filename in filenames])

    def readyFeed(in_feed):
        try:
            in_feed.parseRSS(args.limit, args.destination, args.write_list)
        except KeyError as e:
            print('Feed {} could not be parsed: {}'.format(in_feed.url, e))
            return None
        return in_feed

    def fillEpisode(ep):
        try:
            ep.parseRSSEntry()
            ep.calcPath(args.destination)

            if str(ep.path) in existingFiles:
                ep.status = Status.downloaded

            if ep.status == Status.pending:
                ep.downloadContent()
                try:
                    ep.writeTags()
                except PodcastException as e:
                    print('Tags could not be written to {} in podcast {}: {}'.format(ep.title, ep.podcast, e))

        except PodcastException as e:
            print('{} in podcast {} failed: {}'.format(ep.title, ep.podcast, e))

    pool = multiprocessing.Pool(args.threads)

    # randomise the feed list, just so there's less chance of a slow group
    random.shuffle(subscribedFeeds)

    setstage('Updating')
    print('Updating feeds...')

    subscribedFeeds = list(tqdm(pool.imap_unordered(readyFeed, subscribedFeeds), total=len(subscribedFeeds)))
    subscribedFeeds = list(filter(None, subscribedFeeds))

    episode_queue = [ep for feed in subscribedFeeds for ep in feed.feed_episodes]
    print('{} episodes found'.format(len(episode_queue)))

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
