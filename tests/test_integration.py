#!/usr/bin/env python3
# coding=utf-8

from pathlib import Path
import argparse

import pytest

import podcastdownloader.__main__ as main


@pytest.mark.parametrize('test_args', (
    [],
))
def test_download_no_feeds(test_args: list[str], tmp_path: Path, capsys: pytest.CaptureFixture):
    parser = argparse.ArgumentParser()
    main.add_parser_options(parser)
    args = parser.parse_args(['-vv', str(tmp_path)] + test_args)
    main.main(args)
    out, err = capsys.readouterr()
    assert 'No feeds have been provided' in err


@pytest.mark.parametrize('test_args', (
    ['-f', 'https://rss.art19.com/wecrashed'],
    ['-f', 'http://feeds.libsyn.com/92106/rss', '-l', '1'],  # knowledge fight
))
def test_download_single_feed(test_args: list[str], tmp_path: Path, capsys: pytest.CaptureFixture):
    parser = argparse.ArgumentParser()
    main.add_parser_options(parser)
    args = parser.parse_args(['-vv', str(tmp_path)] + test_args)
    main.main(args)
    out, err = capsys.readouterr()
    assert 'Failed to download' not in err
    pass
