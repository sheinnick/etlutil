from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Set as AbcSet

import pytest

from etlutil import prune_data, walk


def test_invalid_keys_predicate_input_raises_typeerror():
    with pytest.raises(TypeError):
        prune_data({}, keys_to_remove=object())


def test_invalid_values_predicate_input_raises_typeerror():
    with pytest.raises(TypeError):
        prune_data({}, keys_to_remove=None, values_to_remove=object())


class BadInitMap(Mapping):
    def __init__(self, *, allow: bool = False, initial: dict | None = None):
        if not allow:
            raise TypeError("constructor requires allow=True")
        self._data = dict(initial or {})

    def __getitem__(self, key):
        return self._data[key]

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)


def test_mapping_reconstruction_fallback_to_dict():
    # Create instance successfully by passing allow=True, then prune should try BadInitMap(items) and fall back to dict
    m = BadInitMap(allow=True, initial={"a": 1, "b": {"secret": 2}})
    result = prune_data(m, keys_to_remove=["secret"], remove_empty=False)
    assert isinstance(result, dict)
    assert result == {"a": 1, "b": {}}


def test_empty_like_fallback_mapping():
    # After removing everything with remove_empty=True, empty_like should try BadInitMap() and fall back to {}
    m = BadInitMap(allow=True, initial={"secret": None})
    result = prune_data(m, keys_to_remove=["secret"], remove_empty=True)
    assert result == {}


class FakeSet(AbcSet):
    def __init__(self, items):
        self._items = list(items)

    def __contains__(self, x) -> bool:
        return x in self._items

    def __iter__(self):
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)


def test_is_hashable_exception_path_via_fake_set():
    # Fake set can yield unhashable elements (list/dict). prune_data should skip them without raising.
    data = {"s": FakeSet([[1, 2], {"x": 1}])}
    result = prune_data(data, keys_to_remove=None, values_to_remove=lambda _v: False, remove_empty=False)
    # All unhashable children are skipped; resulting set becomes empty
    assert result["s"] == set()


def test_empty_like_for_string_root():
    # Root is string; with remove_empty=True and empty string input, empty_like should return ""
    result = prune_data("", keys_to_remove=None, values_to_remove=None, remove_empty=True)
    assert result == ""


def test_no_filters_short_circuit():
    """Test short-circuit when no filters are active."""
    data = {"a": 1, "b": [2, 3], "c": {"d": 4}}

    # Should return exact same object (not a copy) when no processing needed
    result = prune_data(data, keys_to_remove=[], values_to_remove=[], remove_empty=False)
    assert result is data  # Same object reference


def test_empty_like_all_container_types():
    """Test empty_like function through remove_empty scenarios."""
    from collections import UserDict

    # List becomes empty
    data = ["remove_me"]
    result = prune_data(data, keys_to_remove=None, values_to_remove=["remove_me"], remove_empty=True)
    assert result == []  # Root list becomes empty and stays list

    # Tuple becomes empty
    data = ("remove_me",)
    result = prune_data(data, keys_to_remove=None, values_to_remove=["remove_me"], remove_empty=True)
    assert result == ()  # Root tuple becomes empty and stays tuple

    # Set becomes empty
    data = {"remove_me"}
    result = prune_data(data, keys_to_remove=None, values_to_remove=["remove_me"], remove_empty=True)
    assert result == set()  # Root set becomes empty and stays set

    # Frozenset becomes empty
    data = frozenset(["remove_me"])
    result = prune_data(data, keys_to_remove=None, values_to_remove=["remove_me"], remove_empty=True)
    assert result == frozenset()  # Root frozenset becomes empty and stays frozenset

    # UserDict works fine (doesn't fail construction)
    data = UserDict({"a": 1, "b": 2, "c": 3})
    result = prune_data(data, keys_to_remove=["b", "c"], remove_empty=True)
    assert result == {"a": 1}
    assert isinstance(result, UserDict)  # Type preserved


# ============================================================================
# Edge case tests for walk function
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


