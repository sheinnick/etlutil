from __future__ import annotations

import re
from collections.abc import Hashable
from copy import deepcopy

import pytest

from etlutil import prune_data, walk


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
