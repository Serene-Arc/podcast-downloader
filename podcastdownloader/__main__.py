#!/bin/usr/env python3

import configparser
import argparse
import xml.etree.ElementTree as et
import pathlib
from podcastdownloader.feed import Feed
from stageprint import setstage, print, input

parser = argparse.ArgumentParser()


if __name__ == "__main__":
    parser.add_argument('-d', '--destination', help='directory to store downloads')
    parser.add_argument('-f', '--feed', action='append', help='feed to download')
    parser.add_argument('-t', '--threads', type=int, default=3, help='number of concurrent downloads')
    parser.add_argument('-o', '--opml', help='location of an OPML file to load')
    parser.add_argument('-s', '--split-podcasts', action='store_true',
                        help='flag to split the podcasts into different directories')
    parser.add_argument('-n', '--number', type=int, default=-1, help='number of episodes to download')

    args = parser.parse_args()
    setstage('Loading')
    feeds = []

    if args.opml:
        feed_file = pathlib.Path(args.opml)
        feed_tree = et.parse(feed_file)
        for found_feed in feed_tree.getroot().iter('outline'):
            feeds.append(Feed(found_feed['xmlUrl']))
            print('Feed {} added'.format(found_feed['xmlUrl']))
    if args.feed:
        for arg_feed in args.feed:
            feeds.append(Feed(arg_feed))
            print('Feed {} added'.format(arg_feed))

    setstage('Updating')
    for feed in feeds:
        feed.getFeed()
        print('Feed {} updated'.format(feed.title))
