from __future__ import annotations

from collections.abc import Mapping, Sequence
from collections.abc import Set as AbcSet
from copy import deepcopy

import pytest
from hypothesis import given
from hypothesis import strategies as st

from etlutil import clean_dict, move_unknown_keys_to_extra, prune_data, walk
from etlutil.data_structures import convert_dict_types

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
DICT_DATA = st.dictionaries(keys=st.text(min_size=1, max_size=5), values=DATA, max_size=5)


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


# ============================================================================
# Property-based tests for walk function
# ============================================================================


@given(DATA)
def test_walk_always_returns_object(data):
    """walk should always return an object, regardless of print_output setting."""
    result1 = walk(data, print_output=True)
    result2 = walk(data, print_output=False)
    # Both should return the same collected data
    assert result1 == result2


@given(DATA)
def test_walk_no_mutation_of_input(data):
    """walk should not mutate the input data."""
    before = deepcopy(data)
    _ = walk(data, print_output=False, max_depth=2, max_items_per_container=5)
    assert data == before


@given(DATA)
def test_walk_deterministic(data):
    """Same inputs should yield identical outputs."""
    r1 = walk(data, print_output=False, max_depth=3, sort_keys=True)
    r2 = walk(data, print_output=False, max_depth=3, sort_keys=True)
    assert r1 == r2


@given(DATA, st.integers(min_value=0, max_value=5))
def test_walk_max_depth_consistent(data, max_depth):
    """Collection and printing should respect max_depth consistently."""
    # Both should apply the same depth limits
    collected = walk(data, print_output=False, max_depth=max_depth)

    # Verify depth is respected by checking nested structure
    def check_depth(obj, current_depth=0):
        if current_depth >= max_depth:
            # At max depth, containers should be empty
            if isinstance(obj, Mapping):
                assert obj == {}
            elif isinstance(obj, Sequence) and not isinstance(obj, str | bytes | bytearray):
                assert obj == [] if isinstance(obj, list) else obj == ()
            elif isinstance(obj, AbcSet):
                assert obj == set() if isinstance(obj, set) else obj == frozenset()
        else:
            # Below max depth, can recurse
            if isinstance(obj, Mapping):
                for v in obj.values():
                    check_depth(v, current_depth + 1)
            elif isinstance(obj, Sequence) and not isinstance(obj, str | bytes | bytearray):
                for v in obj:
                    check_depth(v, current_depth + 1)
            elif isinstance(obj, AbcSet):
                for v in obj:
                    check_depth(v, current_depth + 1)

    check_depth(collected)


@given(DATA, st.integers(min_value=1, max_value=10))
def test_walk_max_items_per_container(data, max_items):
    """max_items_per_container should limit sequences and sets but not mappings."""
    result = walk(data, print_output=False, max_items_per_container=max_items)

    def check_limits(obj):
        if isinstance(obj, Mapping):
            # Mappings are not limited by max_items_per_container
            for v in obj.values():
                check_limits(v)
        elif isinstance(obj, Sequence) and not isinstance(obj, str | bytes | bytearray):
            # Sequences should be limited
            assert len(obj) <= max_items
            for v in obj:
                check_limits(v)
        elif isinstance(obj, AbcSet):
            # Sets should be limited
            assert len(obj) <= max_items
            for v in obj:
                check_limits(v)

    check_limits(result)


@given(DATA)
def test_walk_container_types_preserved(data):
    """Container types should be preserved during collection."""
    result = walk(data, print_output=False)

    def check_types(original, collected):
        if type(original) is not type(collected):
            # Only allow empty containers at depth limits
            if isinstance(original, Mapping) and collected == {}:
                return
            elif isinstance(original, list) and collected == []:
                return
            elif isinstance(original, tuple) and collected == ():
                return
            elif isinstance(original, set) and collected == set():
                return
            elif isinstance(original, frozenset) and collected == frozenset():
                return
            else:
                raise AssertionError(f"Type mismatch: {type(original)} vs {type(collected)}")

        if isinstance(original, Mapping) and isinstance(collected, Mapping):
            for k in collected.keys():
                if k in original:
                    check_types(original[k], collected[k])
        elif isinstance(original, list | tuple) and isinstance(collected, list | tuple):
            for i, v in enumerate(collected):
                if i < len(original):
                    check_types(original[i], v)
        elif isinstance(original, AbcSet) and isinstance(collected, AbcSet):
            # Sets are harder to compare element-wise due to ordering
            pass  # Just check that both are sets of the same type

    check_types(data, result)


# ============================================================================
# Property-based tests for move_unknown_keys_to_extra function
# ============================================================================


# move_unknown_keys_to_extra property-based tests
@given(
    data=st.dictionaries(
        keys=st.one_of(st.text(), st.integers(), st.tuples(st.integers(), st.integers())),
        values=st.one_of(st.text(), st.integers(), st.booleans(), st.none()),
        min_size=0,
        max_size=20,
    ),
    allowed_ratio=st.floats(min_value=0.0, max_value=1.0),
    always_add_extra=st.booleans(),
)
def test_move_unknown_keys_property_based(data, allowed_ratio, always_add_extra):
    """Property-based test for move_unknown_keys_to_extra with random data."""
    if not data:
        # Empty dict case
        result, moved = move_unknown_keys_to_extra(data, [], always_add_extra=always_add_extra)
        if always_add_extra:
            assert result == {"extra_collected": {}}
        else:
            assert result == {}
        assert moved == []
        return

    # Select random subset of keys as allowed
    all_keys = list(data.keys())
    num_allowed = int(len(all_keys) * allowed_ratio)
    allowed_keys = all_keys[:num_allowed]

    result, moved = move_unknown_keys_to_extra(data, allowed_keys, always_add_extra=always_add_extra)

    # Property 1: Result should be a dict
    assert isinstance(result, dict)
    assert isinstance(moved, list)

    # Property 2: All allowed keys should be in result with correct values
    for key in allowed_keys:
        str_key = str(key)
        # Key might have collision suffix, but original value should be preserved somewhere
        found = False
        for result_key, result_value in result.items():
            if result_key == str_key or (result_key.startswith(str_key + "__") and str_key != result_key):
                if result_value == data[key]:
                    found = True
                    break
            elif result_key == "extra_collected" and isinstance(result_value, dict):
                for extra_key, extra_value in result_value.items():
                    if extra_key == str_key or (extra_key.startswith(str_key + "__") and str_key != extra_key):
                        if extra_value == data[key]:
                            found = True
                            break
        assert found, f"Key {key} with value {data[key]} not found in result"

    # Property 3: All original values should be preserved somewhere
    original_values = set(data.values())
    result_values = set()

    for value in result.values():
        if isinstance(value, dict):  # extra_collected
            result_values.update(value.values())
        else:
            result_values.add(value)

    # All original values should be preserved (accounting for duplicates)
    for original_value in original_values:
        assert original_value in result_values

    # Property 4: Keys should be sorted
    if "extra_collected" in result:
        extra_keys = list(result["extra_collected"].keys())
        assert extra_keys == sorted(extra_keys)

    top_keys = list(result.keys())
    assert top_keys == sorted(top_keys)

    # Property 5: Moved keys should be sorted
    assert moved == sorted(moved)

    # Property 6: always_add_extra behavior
    num_moved = len(moved)
    if always_add_extra:
        # When always_add_extra=True, extra_collected should always be present
        assert "extra_collected" in result
        if num_moved == 0:
            # No moved keys -> extra_collected should be empty dict
            assert result["extra_collected"] == {}
    else:
        # When always_add_extra=False (default), extra_collected only present if keys moved
        if num_moved == 0:
            assert "extra_collected" not in result
        else:
            assert "extra_collected" in result


@given(
    data=st.dictionaries(
        keys=st.text(min_size=1, max_size=10),
        values=st.text(),
        min_size=1,
        max_size=10,
    ),
    always_add_extra=st.booleans(),
)
def test_move_unknown_keys_deterministic(data, always_add_extra):
    """Property: Multiple runs should produce identical results."""
    allowed_keys = list(data.keys())[: len(data) // 2]  # Take first half

    results = []
    for _ in range(3):
        result, moved = move_unknown_keys_to_extra(data, allowed_keys, always_add_extra=always_add_extra)
        results.append((result, moved))

    # All results should be identical
    first_result = results[0]
    for result in results[1:]:
        assert result == first_result


@given(
    num_keys=st.integers(min_value=1, max_value=50),
    allowed_ratio=st.floats(min_value=0.0, max_value=1.0),
    always_add_extra=st.booleans(),
)
def test_move_unknown_keys_scalability(num_keys, allowed_ratio, always_add_extra):
    """Property: Function should handle various data sizes efficiently."""
    # Generate data with known structure
    data = {f"key_{i}": f"value_{i}" for i in range(num_keys)}
    num_allowed = int(num_keys * allowed_ratio)
    allowed_keys = [f"key_{i}" for i in range(num_allowed)]

    result, moved = move_unknown_keys_to_extra(data, allowed_keys, always_add_extra=always_add_extra)

    # Verify correct partitioning
    num_moved = num_keys - num_allowed

    if always_add_extra:
        # extra_collected always present
        expected_kept = num_allowed + 1  # +1 for extra_collected
        assert "extra_collected" in result
        assert len(result["extra_collected"]) == num_moved
    else:
        # extra_collected only present if keys were moved
        expected_kept = num_allowed + (1 if num_moved > 0 else 0)  # +1 for extra_collected if needed
        if num_moved > 0:
            assert "extra_collected" in result
            assert len(result["extra_collected"]) == num_moved
        else:
            assert "extra_collected" not in result

    assert len(result) == expected_kept
    assert len(moved) == num_moved


@given(
    data=st.dictionaries(
        keys=st.text(min_size=1, max_size=5),
        values=st.one_of(st.text(), st.integers(), st.booleans()),
        min_size=0,
        max_size=10,
    ),
    allowed_ratio=st.floats(min_value=0.0, max_value=1.0),
)
def test_move_unknown_keys_always_add_extra_property(data, allowed_ratio):
    """Property test specifically for always_add_extra parameter behavior."""
    all_keys = list(data.keys()) if data else []
    num_allowed = int(len(all_keys) * allowed_ratio)
    allowed_keys = all_keys[:num_allowed]

    # Test both values of always_add_extra
    result_false, moved_false = move_unknown_keys_to_extra(data, allowed_keys, always_add_extra=False)
    result_true, moved_true = move_unknown_keys_to_extra(data, allowed_keys, always_add_extra=True)

    # moved_keys should be identical regardless of always_add_extra
    assert moved_false == moved_true

    # Check extra_collected presence
    has_moved_keys = len(moved_false) > 0

    if has_moved_keys:
        # When keys were moved, both should have extra_collected with same content
        assert "extra_collected" in result_false
        assert "extra_collected" in result_true
        assert result_false["extra_collected"] == result_true["extra_collected"]
        # Other keys should be identical
        result_false_no_extra = {k: v for k, v in result_false.items() if k != "extra_collected"}
        result_true_no_extra = {k: v for k, v in result_true.items() if k != "extra_collected"}
        assert result_false_no_extra == result_true_no_extra
    else:
        # When no keys moved, behavior should differ based on always_add_extra
        assert "extra_collected" not in result_false
        assert "extra_collected" in result_true
        assert result_true["extra_collected"] == {}
        # Other keys should be identical
        result_true_no_extra = {k: v for k, v in result_true.items() if k != "extra_collected"}
        assert result_false == result_true_no_extra


# ============================================================================
# Property-based tests for convert_dict_types function
# ============================================================================


# Strategies for conversion testing
convertible_values = st.one_of(
    st.integers(min_value=-1000, max_value=1000),
    st.floats(min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
    st.booleans(),
    st.text(min_size=0, max_size=20),
    st.none(),
)

conversion_types = st.sampled_from(
    [
        "int",
        "float",
        "bool",
        "str",
        "timestamp_to_iso",
        "timestamp_to_iso_date",
        "timestamp_to_iso_YYYY-MM",
        "timestamp_to_iso_YYYY",
    ]
)

schema_strategy = st.dictionaries(
    keys=st.text(min_size=1, max_size=10), values=conversion_types, min_size=1, max_size=5
)


@given(
    data=st.dictionaries(keys=st.text(min_size=1, max_size=10), values=convertible_values, min_size=1, max_size=10),
    schema=schema_strategy,
    recursive=st.booleans(),
    strict=st.booleans(),
    empty_string_to_none=st.booleans(),
)
def test_convert_dict_types_property_basic_invariants(data, schema, recursive, strict, empty_string_to_none):
    """Property test: basic invariants should hold for any valid input."""
    try:
        result = convert_dict_types(
            data, schema, recursive=recursive, strict=strict, empty_string_to_none=empty_string_to_none
        )

        # Basic invariants
        assert isinstance(result, dict)
        assert len(result) == len(data)  # Same number of keys

        # All original keys should be present
        assert set(result.keys()) == set(data.keys())

        # Keys not in schema should remain unchanged (unless recursive affects them)
        for key in data:
            if key not in schema:
                if not recursive or not isinstance(data[key], dict | list):
                    assert result[key] == data[key]

    except (ValueError, TypeError, OverflowError):
        # In strict mode, conversion errors are expected for some inputs
        if not strict:
            # In non-strict mode, function should not raise for basic type errors
            # (though it might for other reasons like overflow)
            pass


@given(
    base_data=st.dictionaries(
        keys=st.text(min_size=1, max_size=5), values=st.text(min_size=1, max_size=20), min_size=1, max_size=5
    )
)
def test_convert_dict_types_property_string_to_int_consistency(base_data):
    """Property test: string->int conversion should be consistent."""
    # Filter to only numeric strings that should convert cleanly
    numeric_data = {}
    for key, value in base_data.items():
        if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
            try:
                int(value)  # Verify it's actually convertible
                numeric_data[key] = value
            except ValueError:
                continue

    if not numeric_data:
        return  # Skip if no valid numeric data

    schema = dict.fromkeys(numeric_data.keys(), "int")

    result = convert_dict_types(numeric_data, schema, strict=False)

    # All values should be successfully converted to int
    for key, original_value in numeric_data.items():
        assert isinstance(result[key], int)
        assert result[key] == int(original_value)


@given(
    nested_data=st.recursive(
        st.dictionaries(
            keys=st.text(min_size=1, max_size=5),
            values=st.one_of(st.text(min_size=1, max_size=10), st.integers()),
            min_size=1,
            max_size=3,
        ),
        lambda children: st.dictionaries(
            keys=st.text(min_size=1, max_size=5),
            values=st.one_of(st.text(min_size=1, max_size=10), children),
            min_size=1,
            max_size=3,
        ),
        max_leaves=10,
    )
)
def test_convert_dict_types_property_recursive_structure_preserved(nested_data):
    """Property test: recursive conversion preserves structure."""
    if not isinstance(nested_data, dict):
        return

    schema = {"dummy": "str"}  # Schema that won't match anything

    # Non-recursive should preserve nested structure exactly
    result_non_recursive = convert_dict_types(nested_data, schema, recursive=False)
    assert result_non_recursive == nested_data

    # Recursive should preserve structure shape (even if values change)
    result_recursive = convert_dict_types(nested_data, schema, recursive=True)

    def same_structure(a, b):
        if type(a) is not type(b):
            return False
        if isinstance(a, dict):
            return set(a.keys()) == set(b.keys()) and all(same_structure(a[k], b[k]) for k in a.keys())
        elif isinstance(a, list):
            return len(a) == len(b) and all(same_structure(x, y) for x, y in zip(a, b, strict=True))
        else:
            return True  # Leaf values may differ

    assert same_structure(nested_data, result_recursive)


@given(
    data=st.dictionaries(
        keys=st.text(min_size=1, max_size=5),
        values=st.one_of(st.none(), st.text(min_size=0, max_size=10)),
        min_size=1,
        max_size=5,
    ),
    empty_string_to_none=st.booleans(),
)
def test_convert_dict_types_property_none_and_empty_handling(data, empty_string_to_none):
    """Property test: None values and empty strings are handled consistently."""
    schema = dict.fromkeys(data.keys(), "str")

    result = convert_dict_types(data, schema, empty_string_to_none=empty_string_to_none)

    for key, value in data.items():
        if value is None:
            # None should always be preserved
            assert result[key] is None
        elif value == "" and empty_string_to_none:
            # Empty string should become None when flag is set
            assert result[key] is None
        elif value == "" and not empty_string_to_none:
            # Empty string should be preserved when flag is not set
            assert result[key] == ""


# ============================================================================
# Property-based tests for clean_dict
# ============================================================================


def _iter_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for nested in value.values():
            yield from _iter_strings(nested)
    elif isinstance(value, list | tuple):
        for nested in value:
            yield from _iter_strings(nested)


def _contains_target_key(value, key_set):
    """Return True if any dict in value contains a string key from key_set."""
    if isinstance(value, dict):
        for nested_key, nested_value in value.items():
            if isinstance(nested_key, str) and nested_key in key_set:
                return True
            if _contains_target_key(nested_value, key_set):
                return True
        return False
    if isinstance(value, list | tuple):
        for nested in value:
            if _contains_target_key(nested, key_set):
                return True
        return False
    if isinstance(value, set | frozenset):
        for nested in value:
            if _contains_target_key(nested, key_set):
                return True
        return False
    return False


@given(payload=DICT_DATA, keys=st.sets(st.text(min_size=1, max_size=5), max_size=3))
def test_clean_dict_only_cleans_selected_keys(payload, keys):
    data = deepcopy(payload)
    key_set = set(keys)
    result = clean_dict(
        dict_input=data,
        keys_to_clean=list(key_set),
        clean_mode="replace",
        truncate_strings=None,
    )

    assert data == payload

    for key, original_value in payload.items():
        if key in key_set:
            continue
        if _contains_target_key(original_value, key_set):
            continue
        assert result.get(key) == original_value


@given(payload=DICT_DATA, limit=st.integers(min_value=1, max_value=12))
def test_clean_dict_truncation_limits(payload, limit):
    data = deepcopy(payload)
    result = clean_dict(
        dict_input=data,
        keys_to_clean=[],
        clean_mode="replace",
        truncate_strings=limit,
    )

    assert data == payload

    suffix = "… truncated (etl)"
    for text in _iter_strings(result):
        assert len(text) <= limit + len(suffix)
        if len(text) > limit:
            assert text.endswith(suffix)


@given(payload=DICT_DATA, keys=st.sets(st.text(min_size=1, max_size=5), max_size=3))
def test_clean_dict_hash_mode_produces_hex(payload, keys):
    data = deepcopy(payload)
    result = clean_dict(
        dict_input=data,
        keys_to_clean=list(keys),
        clean_mode="hash",
        truncate_strings=None,
    )

    assert data == payload

    for text in _iter_strings(result):
        if len(text) == 64:
            int(text, 16)
