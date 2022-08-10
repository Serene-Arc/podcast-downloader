#!/usr/bin/env python3
# coding=utf-8

from pathlib import Path

import pytest
from click.testing import CliRunner

from podcastdownloader.__main__ import cli


@pytest.mark.parametrize('test_args', (
    [],
))
def test_download_no_feeds(test_args: list[str], tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(cli, ['download', '-vv', str(tmp_path)] + test_args)
    assert result.exit_code == 0
    assert 'No feeds have been provided' in result.output


@pytest.mark.parametrize('test_args', (
    ['-f', 'https://rss.art19.com/wecrashed'],
    ['-f', 'http://feeds.libsyn.com/92106/rss', '-l', '1'],  # knowledge fight
))
def test_download_single_feed(test_args: list[str], tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(cli, ['download', '-vv', str(tmp_path)] + test_args)
    assert result.exit_code == 0
