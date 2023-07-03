#!/usr/bin/env python3
# coding=utf-8

import argparse
from pathlib import Path

import pytest

import podcastdownloader.__main__ as main


@pytest.mark.parametrize("test_args", ([],))
def test_download_no_feeds(test_args: list[str], tmp_path: Path, capsys: pytest.CaptureFixture):
    parser = argparse.ArgumentParser()
    main.add_parser_options(parser)
    args = parser.parse_args(["-vv", str(tmp_path)] + test_args)
    main.main(args)
    out, err = capsys.readouterr()
    assert "No feeds have been provided" in err


@pytest.mark.parametrize(
    "test_args",
    (
        ["-f", "https://rss.art19.com/wecrashed"],
        [
            "-f",
            "https://www.omnycontent.com/d/playlist/e73c998e-6e60-432f-8610-ae210140c5b1/e5f91208-cc7e-4726-a312-"
            "ae280140ad11/d64f756d-6d5e-4fae-b24f-ae280140ad36/podcast.rss",
            "-l",
            "1",
        ],  # knowledge fight
    ),
)
def test_download_single_feed(test_args: list[str], tmp_path: Path, capsys: pytest.CaptureFixture):
    parser = argparse.ArgumentParser()
    main.add_parser_options(parser)
    args = parser.parse_args(["-vv", str(tmp_path)] + test_args)
    main.main(args)
    out, err = capsys.readouterr()
    assert "Failed to download" not in err
    pass
