#!/usr/bin/env python3
# coding=utf-8

import pytest

import podcastdownloader.utility_functions as util


@pytest.mark.parametrize(('test_input_string', 'expected'), (
    ('', None),
    ('\n', None),
    ('   \n', None),
    ('#test', None),
    ('# test', None),
    ('  #test', None),
    ('  # test', None),
))
def test_clean_text_line_non_feeds(test_input_string: str, expected: str):
    result = util._clean_text_line(test_input_string)
    assert result == expected


@pytest.mark.parametrize(('test_input_string', 'expected'), (
    ('https://www.example.com/test', 'https://www.example.com/test'),
    ('  https://www.example.com/test', 'https://www.example.com/test'),
    ('https://www.example.com/test#random', 'https://www.example.com/test#random'),
    ('https://www.example.com/test/feed.rss # test comment', 'https://www.example.com/test/feed.rss'),
    ('   https://www.example.com/test/feed.rss # test comment', 'https://www.example.com/test/feed.rss'),
    ('https://www.example.com/test/feed.rss\t # test comment', 'https://www.example.com/test/feed.rss'),
))
def test_clean_text_line_good(test_input_string: str, expected: str):
    result = util._clean_text_line(test_input_string)
    assert result == expected
