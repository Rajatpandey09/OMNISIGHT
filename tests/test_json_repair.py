import json
import pytest
from vision.analyzer import extract_json, parse_model_json


def test_trailing_comma_is_repaired():
    data, repaired = parse_model_json('{"a": 1,\n}')
    assert data == {"a": 1}
    assert repaired is True


def test_valid_json_is_untouched():
    data, repaired = parse_model_json('{"a": "x, }"}')
    assert data == {"a": "x, }"}
    assert repaired is False


def test_garbage_still_fails():
    with pytest.raises(json.JSONDecodeError):
        parse_model_json("not json")


def test_extract_json_is_strict():
    # extract_json no longer repairs; only parse_model_json does
    with pytest.raises(json.JSONDecodeError):
        extract_json('{"a": 1,}')
