from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def jira_item_session(fixtures_dir: Path) -> dict:
    with (fixtures_dir / "jira_item.json").open("r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture()
def jira_item(jira_item_session: dict) -> dict:
    return deepcopy(jira_item_session)


@pytest.fixture(scope="session")
def walk_example_session(fixtures_dir: Path) -> dict:
    with (fixtures_dir / "walk_example.json").open("r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture()
def walk_example(walk_example_session: dict) -> dict:
    return deepcopy(walk_example_session)


BASE_SAMPLE_DICT: dict = {
    "import_top": 1,
    "keep": 2,
    3: "int_key",
    (1, 2): "tuple_key",
    "nested": {
        "import_inner": 10,
        4: "int_inner",
    },
    "arr": [
        {"import_item": True, 5: "int_in_item"},
        {"keep2": True},
    ],
}


@pytest.fixture()
def sample_dict() -> dict:
    return deepcopy(BASE_SAMPLE_DICT)


@pytest.fixture()
def sample_dict_factory() -> callable:
    def merge_nested(dst: object, src: object) -> object:
        if isinstance(dst, dict) and isinstance(src, dict):
            out: dict = dict(dst)
            for k, v in src.items():
                if k in out:
                    out[k] = merge_nested(out[k], v)
                else:
                    out[k] = deepcopy(v)
            return out
        return deepcopy(src)

    def make(**overrides: object) -> dict:
        data = deepcopy(BASE_SAMPLE_DICT)
        if overrides:
            data = merge_nested(data, overrides)  # type: ignore[assignment]
        return data

    return make


@pytest.fixture(scope="session")
def load_json_fixture(fixtures_dir: Path):
    def loader(name: str) -> dict:
        with (fixtures_dir / name).open("r", encoding="utf-8") as f:
            return json.load(f)
    return loader


