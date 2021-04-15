#!/usr/bin/env python3
# coding=utf-8

from pathlib import Path

import pytest
from click.testing import CliRunner

from podcastdownloader.__main__ import cli


@pytest.mark.parametrize('test_arguments', (
    ['-t', '1', '-l', '1', '-f', 'https://rss.art19.com/wecrashed'],
))
def test_cli_download_general(test_arguments: list[str], tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(cli, ['download', '-vv', str(tmp_path), '--suppress-progress'] + test_arguments)
    assert result.exit_code == 0
    assert 'downloaded from podcast' in result.output


@pytest.mark.skip
@pytest.mark.parametrize('test_arguments', (
    [''],
))
def test_cli_tag(test_arguments: list[str], tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(cli, ['download', '-vv', str(tmp_path), '--suppress-progress'] + test_arguments)
    assert result.exit_code == 0
