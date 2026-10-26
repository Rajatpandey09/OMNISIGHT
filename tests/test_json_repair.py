import json
import pytest
from vision.analyzer import extract_json


def test_trailing_comma_is_repaired():
    assert extract_json('{"a": 1,\n}') == {"a": 1}


def test_valid_json_is_untouched():
    assert extract_json('{"a": "x, }"}') == {"a": "x, }"}


def test_garbage_still_fails():
    with pytest.raises(json.JSONDecodeError):
        extract_json("not json")
