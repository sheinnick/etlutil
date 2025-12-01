from __future__ import annotations

import hashlib
import re
from collections.abc import Hashable
from copy import deepcopy
from datetime import date, datetime

import pytest

from etlutil import clean_dict, move_unknown_keys_to_extra, prune_data, walk
from etlutil.data_structures import ConvertType, convert_dict_types


# Basic key removal and depth
def test_remove_keys_any_depth_basic():
    data = {
        "a": 1,
        "x": {"secret": 2, "keep": 3},
        "y": [{"secret": 4}, {"z": {"secret": 5}}],
    }
    result = prune_data(data, keys_to_remove=["secret"])
    assert result == {"a": 1, "x": {"keep": 3}, "y": [{}, {"z": {}}]}


@pytest.mark.parametrize(
    "max_depth,expected",
    [
        (0, {"a": 1, "x": {"secret": 2}, "y": [{"secret": 4}, {"z": {"secret": 5}}]}),
        (1, {"a": 1, "x": {}, "y": [{"secret": 4}, {"z": {"secret": 5}}]}),
        (2, {"a": 1, "x": {}, "y": [{}, {"z": {"secret": 5}}]}),
        (3, {"a": 1, "x": {}, "y": [{}, {"z": {}}]}),
        (None, {"a": 1, "x": {}, "y": [{}, {"z": {}}]}),
    ],
)
def test_depth_semantics(max_depth, expected):
    data = {
        "a": 1,
        "x": {"secret": 2},
        "y": [{"secret": 4}, {"z": {"secret": 5}}],
    }
    assert prune_data(data, ["secret"], max_depth=max_depth) == expected


# Empty values cleanup
def test_remove_empty_values_enabled():
    data = {
        "a": None,
        "b": "",
        "c": [],
        "d": {},
        "e": set(),
        "f": 0,
        "g": False,
        "h": [None, "", [], {}, set(), 0, False, 3],
        "i": [None, "", False, 3, [], {}, set(), 0],
        "j": (None, "", False, 3, [], {}, set(), 0),
    }
    result = prune_data(data, keys_to_remove=[], remove_empty=True)
    assert result == {"f": 0, "g": False, "h": [0, False, 3], "i": [False, 3, 0], "j": (False, 3, 0)}


# Container types and immutability
def test_preserve_container_types_and_sets_hashable_only():
    data = {
        "lst": [1, {"k": 2}],
        "tpl": (1, {"k": 2}),
        "st": {1, frozenset({2})},
    }
    result = prune_data(data, keys_to_remove=["k"], remove_empty=True)
    assert isinstance(result["lst"], list)
    assert isinstance(result["tpl"], tuple)
    assert isinstance(result["st"], set)
    assert result["lst"] == [1]
    assert result["tpl"] == (1,)
    assert result["st"] == {1, frozenset({2})}


def test_input_immutability():
    data = {"x": {"secret": 1}, "y": ["a", {"secret": 2}]}
    original = deepcopy(data)
    _ = prune_data(data, ["secret"], remove_empty=False)
    assert data == original


def test_empty_root_result_returns_empty_dict():
    data = {"secret": None}
    result = prune_data(data, ["secret"], remove_empty=True)
    assert result == {}


def test_negative_depth_raises():
    with pytest.raises(ValueError):
        prune_data({}, [], max_depth=-1)


@pytest.mark.parametrize(
    "data, expected, expected_type",
    [
        ([{"secret": 1}, [], 0], [0], list),
        (({"secret": 1}, [], 0), (0,), tuple),
    ],
)
def test_root_container_type_preserved_seq(data, expected, expected_type):
    result = prune_data(data, ["secret"], remove_empty=True, max_depth=None)
    assert isinstance(result, expected_type)
    assert result == expected


@pytest.mark.parametrize(
    "data, expected, expected_type",
    [
        ({frozenset({1}), 0}, {0, frozenset({1})}, set),
        (frozenset({0, frozenset({1})}), frozenset({0, frozenset({1})}), frozenset),
    ],
)
def test_root_container_type_preserved_sets(data, expected, expected_type):
    result = prune_data(data, ["secret"], remove_empty=True, max_depth=None)
    assert isinstance(result, expected_type)
    assert result == expected


# Predicates and advanced filtering
def test_values_iterable_removal_across_containers():
    data = {
        "lst": [0, 1, "x"],
        "tpl": (0, 1, "x"),
        "st": {0, 1, "x"},
        "fs": frozenset({0, 1, "x"}),
        "mp": {"a": 0, "b": 1, "c": "x"},
    }
    result = prune_data(data, keys_to_remove=[], remove_empty=False, values_to_remove=[0, "x"])
    assert result["lst"] == [1]
    assert result["tpl"] == (1,)
    assert result["st"] == {1}
    assert result["fs"] == frozenset({1})
    assert result["mp"] == {"b": 1}


def test_value_predicate_after_recursion_removes_empty_children():
    data = {"a": {"secret": 1}, "b": 2}

    def value_predicate(v: object) -> bool:
        if isinstance(v, dict):
            return len(v) == 0
        return False

    result = prune_data(data, keys_to_remove=["secret"], remove_empty=False, values_to_remove=value_predicate)
    assert result == {"b": 2}


def test_keys_predicate_respects_depth():
    data = {
        "secret": 0,
        "keep": 0,
        "child": {
            "secret": 1,
            "inner": {
                "secret": 2,
            },
        },
    }

    def key_predicate(k: Hashable) -> bool:
        return k == "secret"

    result = prune_data(data, keys_to_remove=key_predicate, remove_empty=False, max_depth=1)
    assert "secret" not in result
    assert "secret" not in result["child"]
    assert "secret" in result["child"]["inner"]


def test_value_predicate_depth_for_sequence_elements():
    depths: list[int] = []

    def value_predicate(_v: object) -> bool:
        depths.append(1)
        return False

    data = {"a": [0, 1, 2]}
    _ = prune_data(data, keys_to_remove=[], remove_empty=False, values_to_remove=value_predicate, max_depth=1)
    assert depths == [1, 1, 1]


def test_key_predicate_with_non_string_keys(sample_dict: dict):
    result = prune_data(
        sample_dict,
        keys_to_remove=lambda key: isinstance(key, str) and key.startswith("import_"),
        remove_empty=False,
    )

    assert "import_top" not in result
    assert 3 in result and result[3] == "int_key"
    assert (1, 2) in result and result[(1, 2)] == "tuple_key"
    assert "import_inner" not in result["nested"]
    assert 4 in result["nested"] and result["nested"][4] == "int_inner"
    assert "import_item" not in result["arr"][0]
    assert 5 in result["arr"][0] and result["arr"][0][5] == "int_in_item"


def test_keep_only_int_keys(sample_dict: dict):
    result = prune_data(
        sample_dict,
        keys_to_remove=lambda key: not isinstance(key, int),
        remove_empty=False,
    )
    assert result == {3: "int_key"}


def test_keep_only_array_values(sample_dict: dict):
    result = prune_data(
        sample_dict,
        keys_to_remove=None,
        values_to_remove=lambda v: not isinstance(v, list),
        remove_empty=False,
    )
    assert result == {"arr": []}


def test_keep_only_values_with_email(sample_dict_factory):
    data = sample_dict_factory(keep="hello test@test.test. how are you?")
    pattern = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

    def value_predicate(v: object) -> bool:
        return not (isinstance(v, str) and pattern.search(v))

    result = prune_data(
        data,
        keys_to_remove=None,
        values_to_remove=value_predicate,
        remove_empty=True,
    )
    assert result == {"keep": "hello test@test.test. how are you?"}


# Jira fixture tests
def test_remove_specific_keys_from_jira_item(jira_item: dict):
    keys_to_remove = ["import_uuid_generated", "import_datetime", "import_last_days"]
    result = prune_data(jira_item, keys_to_remove=keys_to_remove, remove_empty=True)
    assert "import_uuid_generated" not in result
    assert "import_datetime" not in result
    assert "import_last_days" not in result


def test_values_removal_in_items_list(jira_item: dict):
    def value_predicate(v: object) -> bool:
        if isinstance(v, dict):
            if v.get("toString") == "3":
                return True
            if v.get("field") == "timespent":
                return True
        return False

    result = prune_data(jira_item, keys_to_remove=[], values_to_remove=value_predicate, remove_empty=True)
    assert all(item.get("toString") != "3" and item.get("field") != "timespent" for item in result["items"])


def test_remove_keys_with_import_prefix(jira_item: dict):
    result = prune_data(
        jira_item,
        keys_to_remove=lambda key: isinstance(key, str) and key.startswith("import_"),
        remove_empty=True,
    )
    assert "import_uuid_generated" not in result
    assert "import_datetime" not in result
    assert "import_last_days" not in result


# Walk function tests
def test_walk_basic_tree_output(walk_example: dict, capsys):
    walk(walk_example)
    captured = capsys.readouterr()
    output = captured.out

    assert "[dict]" in output
    assert "├─ a: 1" in output
    assert "├─ e [list]" in output
    assert "├─ b [dict]" in output
    assert "└─ g [list]" in output


def test_walk_with_show_types(walk_example: dict, capsys):
    walk(walk_example, show_types=True)
    captured = capsys.readouterr()
    output = captured.out

    assert "(int)" in output
    assert "(str)" in output
    # dict types are shown as [dict] not (dict)
    assert "[dict]" in output


def test_walk_with_show_lengths(walk_example: dict, capsys):
    walk(walk_example, show_lengths=True)
    captured = capsys.readouterr()
    output = captured.out

    assert "len=" in output
    # size= is only shown for sets, but g is now a list
    assert "len=2" in output  # for list g


def test_walk_with_max_depth(walk_example: dict, capsys):
    walk(walk_example, max_depth=1)
    captured = capsys.readouterr()
    output = captured.out

    # should show top level but not nested contents
    assert "├─ e [list]" in output
    assert "├─ b [dict]" in output
    assert "└─ g [list]" in output

    # should not show nested items
    assert "├─ [0] [dict]" not in output
    assert "├─ c [list]" not in output


def test_walk_with_max_items_per_container(walk_example: dict, capsys):
    walk(walk_example, max_items_per_container=2)
    captured = capsys.readouterr()
    output = captured.out

    # should show only first 2 items in lists/sets
    # Note: max_items_per_container only affects sequences and sets, not mappings
    assert "├─ [0] [dict]" in output
    assert "└─ [1]: 4" in output
    # third item in list e should not appear (max_items=2 means only [0] and [1])
    assert "├─ [2]" not in output


def test_walk_with_quote_strings(walk_example: dict, capsys):
    walk(walk_example, quote_strings=True)
    captured = capsys.readouterr()
    output = captured.out

    assert '"x"' in output  # string value should be quoted


def test_walk_with_truncate_value_len(walk_example: dict, capsys):
    walk(walk_example, truncate_value_len=1)
    captured = capsys.readouterr()
    output = captured.out

    # long values should be truncated
    assert "…" in output


def test_walk_with_sort_keys(walk_example: dict, capsys):
    walk(walk_example, sort_keys=True)
    captured = capsys.readouterr()
    output = captured.out

    # keys should be sorted alphabetically
    lines = output.split("\n")
    key_lines = [line for line in lines if "├─ " in line or "└─ " in line]
    key_lines = [line for line in key_lines if not line.strip().startswith("│")]

    # extract keys from lines (only dict keys, not list indices)
    keys = []
    for line in key_lines:
        if "├─ " in line:
            key = line.split("├─ ")[1].split(":")[0].split(" [")[0]
            # only include actual dict keys, not list indices like [0], [1]
            if not key.startswith("["):
                keys.append(key)
        elif "└─ " in line:
            key = line.split("└─ ")[1].split(":")[0].split(" [")[0]
            if not key.startswith("["):
                keys.append(key)

    # check if dict keys are sorted
    assert keys == sorted(keys)


def test_walk_with_set_order_stable(walk_example: dict, capsys):
    walk(walk_example, set_order="stable")
    captured = capsys.readouterr()
    output = captured.out

    # should show list items in stable order
    assert "├─ [0]: 1" in output
    assert "├─ [1]: 2" in output


def test_walk_with_custom_writer(walk_example: dict):
    output_lines = []

    def custom_writer(line: str) -> None:
        output_lines.append(line)

    walk(walk_example, writer=custom_writer)

    assert len(output_lines) > 0
    assert any("[dict]" in line for line in output_lines)


def test_walk_jira_item_basic(jira_item: dict, capsys):
    walk(jira_item, max_depth=2)
    captured = capsys.readouterr()
    output = captured.out

    assert "[dict]" in output
    assert "├─ id: 10000004" in output
    assert "├─ author [dict]" in output
    assert "├─ items [list]" in output


def test_walk_jira_item_with_show_types(jira_item: dict, capsys):
    walk(jira_item, show_types=True, max_depth=1)
    captured = capsys.readouterr()
    output = captured.out

    assert "(str)" in output
    assert "(int)" in output


def test_walk_jira_item_with_show_lengths(jira_item: dict, capsys):
    walk(jira_item, show_lengths=True, max_depth=1)
    captured = capsys.readouterr()
    output = captured.out

    assert "len=" in output
    # size= is only shown for sets, jira_item doesn't have sets
    assert "len=10" in output  # for root dict


def test_walk_jira_item_max_items_limit(jira_item: dict, capsys):
    walk(jira_item, max_items_per_container=2, max_depth=2)
    captured = capsys.readouterr()
    output = captured.out

    # should show only first 2 items in the items list
    # Note: max_items_per_container only affects sequences and sets, not mappings
    assert "├─ [0] [dict]" in output
    assert "└─ [1] [dict]" in output
    assert "├─ [2]" not in output  # third item should not appear


def test_walk_empty_containers():
    empty_data = {"empty_list": [], "empty_dict": {}, "empty_set": set()}

    output_lines = []

    def custom_writer(line: str) -> None:
        output_lines.append(line)

    walk(empty_data, writer=custom_writer)

    assert any("empty_list [list]" in line for line in output_lines)
    assert any("empty_dict [dict]" in line for line in output_lines)
    assert any("empty_set [set]" in line for line in output_lines)


def test_walk_nested_structure():
    nested_data = {"level1": {"level2": {"level3": [1, 2, 3]}}}

    output_lines = []

    def custom_writer(line: str) -> None:
        output_lines.append(line)

    walk(nested_data, writer=custom_writer)

    # should show all levels
    assert any("level1 [dict]" in line for line in output_lines)
    assert any("level2 [dict]" in line for line in output_lines)
    assert any("level3 [list]" in line for line in output_lines)
    assert any("├─ [0]: 1" in line for line in output_lines)


# Tests for new collection functionality
def test_walk_returns_collected_object(walk_example: dict):
    result = walk(walk_example, print_output=False)

    # Should return the collected object
    assert result == walk_example


def test_walk_with_print_output_false_no_printing(walk_example: dict, capsys):
    result = walk(walk_example, print_output=False)
    captured = capsys.readouterr()

    # Should not print anything
    assert captured.out == ""
    # Should return the collected object
    assert result == walk_example


def test_walk_with_print_output_true_prints_and_returns(walk_example: dict, capsys):
    result = walk(walk_example, print_output=True)
    captured = capsys.readouterr()

    # Should print the tree
    assert "[dict]" in captured.out
    # Should also return the collected object
    assert result == walk_example


def test_walk_collection_respects_max_items_per_container():
    data = {"a": 1, "b": [1, 2, 3, 4, 5], "c": {"d": "x"}}
    result = walk(data, print_output=False, max_items_per_container=3)

    # List should be truncated to 3 items
    assert result == {"a": 1, "b": [1, 2, 3], "c": {"d": "x"}}


def test_walk_collection_respects_max_depth():
    data = {"level1": {"level2": {"level3": [1, 2, 3]}}}

    # max_depth=1: can enter level1 dict, but level2 becomes empty dict
    result = walk(data, print_output=False, max_depth=1)
    expected = {"level1": {}}  # level2 dict becomes empty due to depth limit
    assert result == expected

    # max_depth=2: can enter level2 dict, but level3 becomes empty list
    result = walk(data, print_output=False, max_depth=2)
    expected = {"level1": {"level2": {}}}  # level3 list becomes empty due to depth limit
    assert result == expected


def test_walk_collection_with_sets():
    data = {"a": 1, "b": {1, 2, 3, 4, 5}, "c": "text"}
    result = walk(data, print_output=False, max_items_per_container=3)

    # Set should be truncated to 3 items (but order may vary)
    assert result["a"] == 1
    assert result["c"] == "text"
    assert len(result["b"]) == 3
    assert isinstance(result["b"], set)


def test_walk_collection_preserves_container_types():
    data = {"list": [1, 2, 3], "tuple": (4, 5, 6), "set": {7, 8, 9}, "frozenset": frozenset([10, 11, 12])}
    result = walk(data, print_output=False)

    assert isinstance(result["list"], list)
    assert isinstance(result["tuple"], tuple)
    assert isinstance(result["set"], set)
    assert isinstance(result["frozenset"], frozenset)


@pytest.mark.parametrize("max_depth", [None, 1, 2])
@pytest.mark.parametrize("max_items_per_container", [None, 1, 2])
def test_walk_collection_with_jira_data(jira_item: dict, max_depth, max_items_per_container):
    """Test walk collection behavior with different max_depth and max_items_per_container values."""
    result = walk(jira_item, print_output=False, max_depth=max_depth, max_items_per_container=max_items_per_container)

    # Should always return a dict at root level
    assert isinstance(result, dict)

    # Check behavior based on max_depth
    if max_depth is None:
        # No depth limit - should have full nested structure
        assert isinstance(result["author"], dict)
        assert len(result["author"]) == 3  # accountId, displayName, emailAddress
        assert isinstance(result["items"], list)
    elif max_depth == 1:
        # Depth 1 - nested containers should be empty
        assert result["author"] == {}
        assert result["items"] == []
        # Primitives should remain
        assert result["id"] == "10000004"
        assert result["created"] == "2024-11-07T16:35:51.592+0300"
    elif max_depth == 2:
        # Depth 2 - should show one level of nesting
        assert isinstance(result["author"], dict)
        assert len(result["author"]) == 3
        assert isinstance(result["items"], list)
        # Items should contain dicts but they should be empty (depth limit reached)
        if max_items_per_container is None:
            assert len(result["items"]) == 3
        elif max_items_per_container == 1:
            assert len(result["items"]) == 1
        elif max_items_per_container == 2:
            assert len(result["items"]) == 2

        # Each item should be an empty dict due to depth limit
        for item in result["items"]:
            assert item == {}

    # Check behavior based on max_items_per_container
    if max_depth != 1:  # Skip this check when depth=1 as items will be empty
        if max_items_per_container is None:
            # No item limit - should have all 3 items
            if max_depth is None or max_depth >= 2:
                assert len(result["items"]) == 3
        elif max_items_per_container == 1:
            # Should have only 1 item
            if max_depth is None or max_depth >= 2:
                assert len(result["items"]) == 1
        elif max_items_per_container == 2:
            # Should have only 2 items
            if max_depth is None or max_depth >= 2:
                assert len(result["items"]) == 2


# ============================================================================
# tests for move_unknown_keys_to_extra function
# ============================================================================


# move_unknown_keys_to_extra basic functionality tests
def test_move_unknown_keys_basic():
    """Basic whitelist filtering: keep allowed keys, move others to extra."""
    data = {"id": 123, "name": "alex", "age": 30, "city": "berlin"}
    result, moved = move_unknown_keys_to_extra(data, ["id", "name"])

    expected = {
        "extra_collected": {"age": 30, "city": "berlin"},
        "id": 123,
        "name": "alex",
    }
    assert result == expected
    assert set(moved) == {"age", "city"}


def test_move_unknown_keys_all_allowed():
    """When all keys are in whitelist, no extra_collected should be created."""
    data = {"id": 123, "name": "alex"}
    result, moved = move_unknown_keys_to_extra(data, ["id", "name"])

    assert result == {"id": 123, "name": "alex"}
    assert moved == []
    assert "extra_collected" not in result


def test_move_unknown_keys_all_allowed_with_always_add_extra():
    """When all keys are allowed but always_add_extra=True, extra_collected should be empty dict."""
    data = {"id": 123, "name": "alex"}
    result, moved = move_unknown_keys_to_extra(data, ["id", "name"], always_add_extra=True)

    assert result == {"extra_collected": {}, "id": 123, "name": "alex"}
    assert moved == []
    assert "extra_collected" in result
    assert result["extra_collected"] == {}


def test_move_unknown_keys_with_moves_and_always_add_extra():
    """When always_add_extra=True and there are moved keys, extra_collected should contain them."""
    data = {"id": 123, "name": "alex", "age": 30, "city": "berlin"}
    result, moved = move_unknown_keys_to_extra(data, ["id", "name"], always_add_extra=True)

    expected = {
        "extra_collected": {"age": 30, "city": "berlin"},
        "id": 123,
        "name": "alex",
    }
    assert result == expected
    assert set(moved) == {"age", "city"}


def test_move_unknown_keys_none_allowed():
    """When no keys are in whitelist, all should go to extra_collected."""
    data = {"id": 123, "name": "alex"}
    result, moved = move_unknown_keys_to_extra(data, [])

    expected = {"extra_collected": {"id": 123, "name": "alex"}}
    assert result == expected
    assert set(moved) == {"id", "name"}


def test_move_unknown_keys_custom_extra_key():
    """Test using custom extra_key name."""
    data = {"id": 123, "name": "alex", "age": 30}
    result, moved = move_unknown_keys_to_extra(data, ["id"], extra_key="metadata")

    expected = {"id": 123, "metadata": {"age": 30, "name": "alex"}}
    assert result == expected
    assert set(moved) == {"age", "name"}


def test_move_unknown_keys_sorting():
    """Keys should be sorted lexicographically in output."""
    data = {"z": 1, "a": 2, "m": 3, "b": 4}
    result, moved = move_unknown_keys_to_extra(data, ["z"])

    # Top-level keys sorted
    assert list(result.keys()) == ["extra_collected", "z"]
    # Extra keys also sorted
    assert list(result["extra_collected"].keys()) == ["a", "b", "m"]
    # Moved keys sorted
    assert moved == ["a", "b", "m"]


def test_move_unknown_keys_immutability():
    """Original data should not be modified."""
    data = {"id": 123, "name": "alex", "age": 30}
    original = data.copy()
    result, moved = move_unknown_keys_to_extra(data, ["id"])

    # Input unchanged
    assert data == original
    # Result is new object
    assert result is not data


# ============================================================================
# Tests for convert_dict_types function
# ============================================================================


@pytest.mark.parametrize(
    "input_val,target_type,expected",
    [
        ("42", "int", 42),
        ("3.14", "int", 3),
        (True, "int", 1),
        ("3.14", "float", 3.14),
        (42, "float", 42.0),
        (True, "float", 1.0),
        ("true", "bool", True),
        ("1", "bool", True),
        ("yes", "bool", True),
        ("on", "bool", True),
        ("false", "bool", False),
        ("0", "bool", False),
        (1, "bool", True),
        (0, "bool", False),
        (3.14, "bool", True),
        ("2024-12-25", "date", date(2024, 12, 25)),
        ("2024-12-25T15:30:45", "datetime", datetime(2024, 12, 25, 15, 30, 45)),
        ("2024-12-25 15:30:45", "datetime", datetime(2024, 12, 25, 15, 30, 45)),
        ("2024-12-25", "datetime", datetime(2024, 12, 25, 0, 0, 0)),
        ("1735056631", "timestamp_to_iso", "2024-12-24T20:10:31"),
        (1735056631, "timestamp_to_iso", "2024-12-24T20:10:31"),
        ("1735056631", "timestamp_to_iso_date", "2024-12-24"),
        (1735056631, "timestamp_to_iso_date", "2024-12-24"),
        ("1735056631", "timestamp_to_iso_YYYY-MM", "2024-12"),
        (1735056631, "timestamp_to_iso_YYYY-MM", "2024-12"),
        ("1735056631", "timestamp_to_iso_YYYY", "2024"),
        (1735056631, "timestamp_to_iso_YYYY", "2024"),
        (42, "str", "42"),
        (True, "str", "True"),
        (3.14, "str", "3.14"),
    ],
)
def test_convert_single_value(input_val, target_type, expected):
    """Test individual value conversions with parametrized inputs."""
    data = {"test_key": input_val}
    schema = {"test_key": target_type}

    result = convert_dict_types(data, schema)

    assert result["test_key"] == expected


def test_convert_timestamp_to_datetime_object(conversion_data):
    """Test timestamp conversion to datetime object."""
    schema = {"str_timestamp": "timestamp"}

    result = convert_dict_types(conversion_data, schema)

    assert isinstance(result["str_timestamp"], datetime)
    assert result["str_timestamp"] == datetime(2024, 12, 24, 20, 10, 31)


def test_convert_with_enum_schema(conversion_data):
    """Test conversion using ConvertType enum."""
    schema = {
        "str_int": ConvertType.INT,
        "str_float": ConvertType.FLOAT,
        "str_bool_true": ConvertType.BOOL,
        "str_date": ConvertType.DATE,
        "str_timestamp": ConvertType.TIMESTAMP_TO_ISO,
    }

    result = convert_dict_types(conversion_data, schema)

    assert result["str_int"] == 42
    assert result["str_float"] == 3.14
    assert result["str_bool_true"] is True
    assert result["str_date"] == date(2024, 12, 25)
    assert result["str_timestamp"] == "2024-12-24T20:10:31"


@pytest.mark.parametrize(
    "target_type,expected",
    [
        ("timestamp_to_iso_date", "2024-12-24"),
        ("timestamp_to_iso_YYYY-MM", "2024-12"),
        ("timestamp_to_iso_YYYY", "2024"),
    ],
)
def test_convert_timestamp_to_iso_formats(conversion_data, target_type, expected):
    """Test new timestamp to ISO format conversions."""
    schema = {
        "str_timestamp": target_type,
    }

    result = convert_dict_types(conversion_data, schema)
    assert result["str_timestamp"] == expected


@pytest.mark.parametrize(
    "target_type,expected",
    [
        (ConvertType.TIMESTAMP_TO_ISO_DATE, "2024-12-24"),
        (ConvertType.TIMESTAMP_TO_ISO_YYYY_MM, "2024-12"),
        (ConvertType.TIMESTAMP_TO_ISO_YYYY, "2024"),
    ],
)
def test_convert_timestamp_to_iso_formats_with_enum(conversion_data, target_type, expected):
    """Test new timestamp to ISO format conversions using ConvertType enum."""
    schema = {
        "str_timestamp": target_type,
    }

    result = convert_dict_types(conversion_data, schema)
    assert result["str_timestamp"] == expected


def test_convert_recursive_vs_non_recursive(nested_conversion_data):
    """Test recursive vs non-recursive conversion modes."""
    schema = {"top_level": "int", "inner_val": "float", "deep_val": "bool", "value": "int"}

    # Non-recursive - only top level converted
    result_simple = convert_dict_types(nested_conversion_data, schema, recursive=False)
    assert result_simple["top_level"] == 42
    assert result_simple["nested"]["inner_val"] == "3.14"  # Unchanged
    assert result_simple["items"][0]["value"] == "100"  # Unchanged

    # Recursive - all levels converted
    result_recursive = convert_dict_types(nested_conversion_data, schema, recursive=True)
    assert result_recursive["top_level"] == 42
    assert result_recursive["nested"]["inner_val"] == 3.14  # Converted
    assert result_recursive["nested"]["deep_nested"]["deep_val"] is True  # Converted
    assert result_recursive["items"][0]["value"] == 100  # Converted
    assert result_recursive["items"][2]["nested"]["value"] == 300  # Converted


@pytest.mark.parametrize("empty_string_to_none", [True, False])
def test_convert_empty_string_handling(conversion_data, empty_string_to_none):
    """Test empty string handling with parametrized behavior."""
    schema = {"empty_str": "int"}

    result = convert_dict_types(conversion_data, schema, empty_string_to_none=empty_string_to_none)

    if empty_string_to_none:
        assert result["empty_str"] is None
    else:
        assert result["empty_str"] == ""


def test_convert_none_values_preserved(conversion_data):
    """Test that None values are always preserved."""
    schema = {"none_val": "int"}

    result = convert_dict_types(conversion_data, schema)

    assert result["none_val"] is None


def test_convert_unknown_keys_preserved(conversion_data):
    """Test that keys not in schema remain unchanged."""
    schema = {"str_int": "int"}  # Only one key in schema

    result = convert_dict_types(conversion_data, schema)

    assert result["str_int"] == 42  # Converted
    assert result["str_float"] == "3.14"  # Unchanged
    assert result["str_bool_true"] == "true"  # Unchanged


def test_convert_custom_datetime_formats():
    """Test custom datetime format handling."""
    data = {"dt_custom": "25/12/2024 15:30", "dt_iso": "2024-12-25T15:30:45", "dt_standard": "2024-12-25"}
    schema = dict.fromkeys(data.keys(), "datetime")
    custom_formats = ["%d/%m/%Y %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]

    result = convert_dict_types(data, schema, datetime_formats=custom_formats)

    assert result["dt_custom"] == datetime(2024, 12, 25, 15, 30, 0)
    assert result["dt_iso"] == datetime(2024, 12, 25, 15, 30, 45)
    assert result["dt_standard"] == datetime(2024, 12, 25, 0, 0, 0)


def test_convert_fb_api_like_data(fb_api_data):
    """Test conversion of complex FB API-like data."""
    schema = {
        "date_start": "date",
        "impressions": "int",
        "spend": "float",
        "is_active": "bool",
        "created_timestamp": "timestamp",
        "updated_timestamp": "timestamp_to_iso",
        "value": "int",  # For nested conversion
    }

    # Test recursive conversion
    result = convert_dict_types(fb_api_data, schema, recursive=True)

    assert result["date_start"] == date(2025, 8, 27)
    assert result["impressions"] == 42
    assert result["spend"] == 0.100697
    assert result["is_active"] is True
    assert isinstance(result["created_timestamp"], datetime)
    assert result["updated_timestamp"] == "2024-12-24T20:10:31"

    # Check nested conversions
    assert result["actions"][0]["value"] == 2
    assert result["actions"][1]["value"] == 1


# ============================================================================
# Tests for clean_dict function
# ============================================================================


def _sha256_str(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


CLEAN_DICT_CASES = [
    pytest.param(
        {
            "password": "secret",
            "profile": {"password": "nested-secret", "email": "user@example.com"},
        },
        ["password"],
        "replace",
        None,
        {},
        {
            "password": "replaced (etl)",
            "profile": {"password": "replaced (etl)", "email": "user@example.com"},
        },
        id="replace_nested",
    ),
    pytest.param(
        {"token": "", "meta": {"token": "abc"}},
        ["token"],
        "delete",
        None,
        {},
        {"token": "", "meta": {}},
        id="delete_preserves_empty_strings",
    ),
    pytest.param(
        {"secret": "value"},
        ["secret"],
        "empty",
        None,
        {},
        {"secret": None},
        id="empty_mode_sets_none",
    ),
    pytest.param(
        {
            "users": [
                {"email": "secret@example.com"},
                {"email": "second@example.com", "name": "alice"},
            ],
            "audit": ({"email": "tuple@example.com"}, "no-change"),
        },
        ["email"],
        "hash",
        None,
        {},
        {
            "users": [
                {"email": _sha256_str("secret@example.com")},
                {"email": _sha256_str("second@example.com"), "name": "alice"},
            ],
            "audit": ({"email": _sha256_str("tuple@example.com")}, "no-change"),
        },
        id="hash_across_sequences",
    ),
    pytest.param(
        {
            "secret": "value",
            "note": "0123456789ABCDE",
            "nested": {"description": "fedcba9876543210"},
        },
        ["secret"],
        "replace",
        4,
        {"replacement_marker": "[MASKED]", "truncation_suffix": "... trimmed"},
        {
            "secret": "[MAS... trimmed",
            "note": "0123... trimmed",
            "nested": {"description": "fedc... trimmed"},
        },
        id="custom_markers_and_truncation",
    ),
]


@pytest.mark.parametrize(
    "payload,keys_to_clean,clean_mode,truncate_strings,extra_kwargs,expected",
    CLEAN_DICT_CASES,
)
def test_clean_dict_parametrized(payload, keys_to_clean, clean_mode, truncate_strings, extra_kwargs, expected):
    data = deepcopy(payload)
    kwargs = {
        "dict_input": data,
        "keys_to_clean": keys_to_clean,
        "clean_mode": clean_mode,
        "truncate_strings": truncate_strings,
    }
    kwargs.update(extra_kwargs)

    result = clean_dict(**kwargs)

    assert result == expected
    assert data == payload  # Input data remains untouched


def test_clean_dict_farm_fingerprint_mode():
    farmhash = pytest.importorskip("farmhash")
    data = {"session": "abc123"}

    result = clean_dict(
        data,
        keys_to_clean=["session"],
        clean_mode="farm_fingerprint",
        truncate_strings=None,
    )

    assert result["session"] == farmhash.Fingerprint64(b"abc123")


def test_clean_dict_skip_rules_allowlist():
    data = {
        "email": "user@qweqwe.asd",
        "profile": {"email": "blocked@example.com"},
        "token": "keep-123",
        "audit": {"token": "drop-1"},
    }

    result = clean_dict(
        dict_input=data,
        keys_to_clean=["email", "token"],
        clean_mode="replace",
        skip_rules={
            "email": "@qweqwe.asd",
            "token": [{"match": "regex", "pattern": r"^keep-"}],
        },
        truncate_strings=None,
    )

    assert result["email"] == "user@qweqwe.asd"
    assert result["profile"]["email"] == "replaced (etl)"
    assert result["token"] == "keep-123"
    assert result["audit"]["token"] == "replaced (etl)"
