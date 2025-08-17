from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Set as AbcSet

import pytest

from etlutil import prune_data


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


