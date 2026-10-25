import json
from pathlib import Path
from typing import get_args
from vision.schema import IssueType

DATA = json.loads((Path(__file__).parent.parent / "eval" / "labelled_cases.json").read_text())


def test_cases_use_valid_types_and_viewports():
    ids = [c["case_id"] for c in DATA["cases"]]
    assert len(ids) == len(set(ids))
    for c in DATA["cases"]:
        assert c["viewport"] in DATA["viewports"]
        for e in c["expected"]:
            assert e["issue_type"] in get_args(IssueType)


def test_has_clean_cases_for_false_positives():
    assert any(not c["expected"] for c in DATA["cases"])
