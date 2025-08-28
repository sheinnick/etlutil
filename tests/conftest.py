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


# Fixtures for move_unknown_keys_to_extra tests
@pytest.fixture()
def user_data() -> dict:
    """Basic user data for testing."""
    return {"id": 123, "name": "alex", "age": 30, "city": "berlin"}


@pytest.fixture()
def api_response() -> dict:
    """Realistic API response with mixed field types."""
    return {
        "id": "user_12345",
        "name": "John Doe",
        "email": "john@example.com",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-15T12:30:00Z",
        "profile_image_url": "https://example.com/avatar.jpg",
        "preferences": {"theme": "dark", "notifications": True},
        "internal_id": 98765,
        "debug_info": {"trace_id": "abc123", "version": "1.2.3"},
        "temp_session_data": {"csrf_token": "xyz789"},
    }


@pytest.fixture()
def collision_keys_factory():
    """Factory for creating key collision test cases."""

    def make_collision_keys(base_str: str = "1"):
        """Create keys that stringify to same value but are different objects."""

        class CustomKey:
            def __str__(self):
                return base_str

            def __hash__(self):
                return hash(f"custom_{base_str}")

            def __eq__(self, other):
                return isinstance(other, CustomKey)

        # Use tuple to avoid int/str collision in dict
        class TupleKey:
            def __str__(self):
                return base_str

            def __hash__(self):
                return hash(f"tuple_{base_str}")

            def __eq__(self, other):
                return isinstance(other, TupleKey)

        return {
            "string": base_str,
            "tuple": TupleKey(),
            "custom": CustomKey(),
        }

    return make_collision_keys


@pytest.fixture()
def unicode_data() -> dict:
    """Data with unicode keys for testing sorting and handling."""
    return {"ключ": "значение", "key": "value", "🔑": "emoji", "clé": "valeur", "键": "值"}


# Fixtures for convert_dict_types tests
@pytest.fixture()
def conversion_data() -> dict:
    """Basic data for type conversion testing."""
    return {
        "str_int": "42",
        "str_float": "3.14",
        "str_bool_true": "true",
        "str_bool_false": "false",
        "str_date": "2024-12-25",
        "str_datetime": "2024-12-25T15:30:45",
        "str_timestamp": "1735056631",
        "int_val": 42,
        "float_val": 3.14,
        "bool_val": True,
        "none_val": None,
        "empty_str": "",
    }


@pytest.fixture()
def nested_conversion_data() -> dict:
    """Nested data structure for recursive conversion testing."""
    return {
        "top_level": "42",
        "nested": {"inner_val": "3.14", "deep_nested": {"deep_val": "true"}},
        "items": [{"value": "100"}, {"value": "200"}, {"nested": {"value": "300"}}],
    }


@pytest.fixture()
def fb_api_data() -> dict:
    """FB API-like data for complex conversion testing."""
    return {
        "date_start": "2025-08-27",
        "impressions": "42",
        "spend": "0.100697",
        "is_active": "true",
        "created_timestamp": "1735056631",
        "updated_timestamp": 1735056631,
        "empty_field": "",
        "actions": [
            {"action_type": "add_to_wishlist", "value": "2"},
            {"action_type": "omni_add_to_cart", "value": "1"},
        ],
    }
