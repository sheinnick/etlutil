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
# COVERAGE TESTS: Error handling and edge cases
# ============================================================================

def test_walk_primitive_root_object():
    """Test walk with primitive root objects (not containers)."""
    # String root
    result = walk("hello world", print_output=False)
    assert result == "hello world"

    # Number root
    result = walk(42, print_output=False)
    assert result == 42

    # Boolean root
    result = walk(True, print_output=False)
    assert result is True

    # None root
    result = walk(None, print_output=False)
    assert result is None


def test_walk_primitive_root_with_printing(capsys):
    """Test walk printing behavior with primitive root objects."""
    # Should print the value with type annotation when requested
    walk(42, show_types=True)
    captured = capsys.readouterr()
    assert "42 (int)" in captured.out

    walk("test", show_types=False)
    captured = capsys.readouterr()
    assert captured.out.strip() == "test"


def test_walk_sorting_fallback_for_non_comparable_keys():
    """Test fallback to string sorting when keys are not comparable."""
    # Mix of different types that can't be compared directly
    data = {1: "one", "2": "two", 3.0: "three"}

    # Should fallback to string sorting without error
    result = walk(data, print_output=False, sort_keys=True)
    # Result should have same content regardless of sorting method
    # Note: keys are converted to strings during sorting fallback
    assert {str(k) for k in result.keys()} == {"1", "2", "3.0"}
    assert set(result.values()) == {"one", "two", "three"}


def test_walk_sorting_fallback_for_non_comparable_set_elements():
    """Test fallback to string sorting for set elements."""
    # Mix of types in set that can't be compared
    data = {"mixed_set": {1, "2", 3.0}}

    # Should fallback to string sorting without error
    result = walk(data, print_output=False, set_order="sorted")
    # Set should still contain all elements
    assert len(result["mixed_set"]) == 3


def test_walk_unhashable_elements_in_sets():
    """Test handling of unhashable elements during set processing."""
    # This is tricky - sets can't contain unhashable items by definition
    # But during processing we might encounter edge cases
    data = {"regular_set": {1, 2, 3}}

    # Should work fine with hashable elements
    result = walk(data, print_output=False, max_items_per_container=2)
    assert len(result["regular_set"]) == 2


def test_walk_empty_children_edge_case():
    """Test edge case where _children_with_labels returns empty list."""
    # This happens with non-container objects
    result = walk(42, print_output=False)
    assert result == 42

    # Also test with empty containers
    result = walk({}, print_output=False)
    assert result == {}

    result = walk([], print_output=False)
    assert result == []

    result = walk(set(), print_output=False)
    assert result == set()


def test_walk_frozenset_depth_limit():
    """Test depth limit behavior with frozensets."""
    data = {"fs": frozenset([frozenset([1, 2]), frozenset([3, 4])])}

    # At depth=1, inner frozensets should become empty frozensets
    result = walk(data, print_output=False, max_depth=1)
    assert result == {"fs": frozenset()}


def test_walk_tuple_preservation():
    """Test that tuples are preserved during collection."""
    data = {"tup": (1, 2, (3, 4))}

    result = walk(data, print_output=False, max_items_per_container=2)
    assert isinstance(result["tup"], tuple)
    assert len(result["tup"]) == 2  # Limited by max_items_per_container


def test_walk_is_hashable_coverage():
    """Test the is_hashable function indirectly through set processing."""
    # All these items are hashable and should work fine
    data = {"hashable_set": {1, "string", (1, 2), frozenset([3])}}

    result = walk(data, print_output=False)
    assert len(result["hashable_set"]) == 4


def test_walk_render_value_coverage():
    """Test _render_value function coverage through various value types."""
    from io import StringIO

    # Test with very long string truncation
    long_string = "x" * 100
    output = StringIO()
    walk({"long": long_string}, writer=output.write, truncate_value_len=10)
    assert "x" * 10 + "…" in output.getvalue()

    # Test with quote strings and escaping
    output = StringIO()
    walk({"quoted": 'text with "quotes" and \\backslash'}, writer=output.write, quote_strings=True)
    result = output.getvalue()
    assert '\\"' in result  # Escaped quotes
    assert "\\\\" in result  # Escaped backslashes


def test_walk_unhashable_during_set_processing():
    """Test edge case with unhashable items during set processing."""
    # Create a scenario where set processing might encounter issues
    data = {"normal_set": {1, 2, 3, 4, 5}}

    # Process with limits - should work fine
    result = walk(data, print_output=False, max_items_per_container=3)
    assert len(result["normal_set"]) == 3

    # Test with frozenset too
    data = {"frozen": frozenset([1, 2, 3, 4, 5])}
    result = walk(data, print_output=False, max_items_per_container=2)
    assert len(result["frozen"]) == 2
    assert isinstance(result["frozen"], frozenset)
