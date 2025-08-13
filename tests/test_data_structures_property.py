from __future__ import annotations

from collections.abc import Mapping, Sequence
from collections.abc import Set as AbcSet
from copy import deepcopy

import pytest
from hypothesis import given
from hypothesis import strategies as st

from etlutil import prune_data

# Property-based tests (skipped if hypothesis is not installed)
hypothesis = pytest.importorskip("hypothesis")


# Keys allowed in mappings (must be hashable)
hashable_key = st.one_of(
    st.text(),
    st.integers(),
    st.tuples(st.integers(), st.integers()),
)

# Elements allowed in sets/frozensets (must be hashable)
hashable_elem = st.one_of(
    st.text(),
    st.integers(),
    st.booleans(),
    st.tuples(st.integers(), st.integers()),
)


def recursive_data_strategy() -> st.SearchStrategy:
    """Generate nested structures: scalars, lists/tuples, dicts, sets/frozensets."""
    base = st.one_of(st.none(), st.booleans(), st.integers(), st.text())

    def expand(children: st.SearchStrategy) -> st.SearchStrategy:
        # Build containers from already-built children
        lists = st.lists(children, max_size=3)
        tuples = st.lists(children, max_size=3).map(tuple)
        mappings = st.dictionaries(keys=hashable_key, values=children, max_size=3)
        sets = st.sets(elements=hashable_elem, max_size=3)
        frozensets = st.sets(elements=hashable_elem, max_size=3).map(frozenset)
        return st.one_of(lists, tuples, mappings, sets, frozensets)

    return st.recursive(base, expand, max_leaves=10)


DATA = recursive_data_strategy()


@given(DATA)
def test_idempotent_and_type_preserved(data):
    """Running prune_data twice without filters should be idempotent and type-stable."""
    r1 = prune_data(data, keys_to_remove=None, values_to_remove=None, remove_empty=False)
    r2 = prune_data(r1, keys_to_remove=None, values_to_remove=None, remove_empty=False)
    assert type(r1) is type(r2)
    assert r1 == r2


@given(DATA)
def test_no_mutation_of_input(data):
    """Input object must not be mutated by prune_data."""
    before = deepcopy(data)
    _ = prune_data(
        data,
        keys_to_remove=lambda k: isinstance(k, str) and k.startswith("secret_"),
        values_to_remove=lambda v: v == "",
        remove_empty=False,
    )
    assert data == before


@given(DATA)
def test_idempotent_with_filters(data):
    """With fixed filters, repeated application should not change the result further."""

    def key_pred(k: object) -> bool:
        return isinstance(k, str) and k == "x"

    def val_pred(v: object) -> bool:
        return v == ""

    r1 = prune_data(data, keys_to_remove=key_pred, values_to_remove=val_pred, remove_empty=True)
    r2 = prune_data(r1, keys_to_remove=key_pred, values_to_remove=val_pred, remove_empty=True)
    assert r1 == r2


@given(DATA)
def test_noop_when_no_filters_and_no_remove_empty(data):
    """If no filters are provided and remove_empty=False, the function returns input as-is."""
    r = prune_data(data, keys_to_remove=None, values_to_remove=None, remove_empty=False)
    assert r is data


def _is_empty(x: object) -> bool:
    if x is None:
        return True
    if isinstance(x, str):
        return x == ""
    if isinstance(x, Mapping):
        return len(x) == 0
    if isinstance(x, AbcSet):
        return len(x) == 0
    if isinstance(x, Sequence) and not isinstance(x, str | bytes | bytearray):
        return len(x) == 0
    return False


def _walk(x: object):
    yield x
    if isinstance(x, Mapping):
        for v in x.values():
            yield from _walk(v)
    elif isinstance(x, Sequence) and not isinstance(x, str | bytes | bytearray):
        for v in x:
            yield from _walk(v)
    elif isinstance(x, AbcSet):
        for v in x:
            yield from _walk(v)


@given(DATA)
def test_no_empty_when_remove_empty(data):
    """With remove_empty=True, the result must not contain empty containers/values."""
    r = prune_data(data, keys_to_remove=None, values_to_remove=None, remove_empty=True)
    it = iter(_walk(r))
    next(it, None)  # ignore root emptiness (allowed for primitives/fully-pruned roots)
    assert all(not _is_empty(v) for v in it)


@given(DATA)
def test_monotonic_by_depth(data):
    """Pruning deeper from an already pruned result equals pruning deeper from original."""

    def key_pred(k: object) -> bool:
        return isinstance(k, str) and k == "secret"

    r1 = prune_data(data, keys_to_remove=key_pred, values_to_remove=None, remove_empty=False, max_depth=1)
    r2a = prune_data(data, keys_to_remove=key_pred, values_to_remove=None, remove_empty=False, max_depth=2)
    r2b = prune_data(r1, keys_to_remove=key_pred, values_to_remove=None, remove_empty=False, max_depth=2)
    assert r2a == r2b


@given(DATA)
def test_sets_hashable(data):
    """All set/frozenset elements in the result must be hashable."""
    from collections.abc import Set as AbcSet

    r = prune_data(data, keys_to_remove=None, values_to_remove=None, remove_empty=False)

    def check(x: object) -> None:
        if isinstance(x, AbcSet):
            for e in x:
                hash(e)
        elif isinstance(x, dict):
            for v in x.values():
                check(v)
        elif isinstance(x, list | tuple):
            for v in x:
                check(v)

    check(r)


@given(DATA)
def test_deterministic(data):
    """Same inputs and params must yield identical outputs."""
    r1 = prune_data(data, ["k"], remove_empty=True)
    r2 = prune_data(data, ["k"], remove_empty=True)
    assert r1 == r2
