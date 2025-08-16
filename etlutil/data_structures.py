"""Data structures utilities.

Provides `prune_data` to recursively clean common containers by removing selected keys
at any nesting level and optionally dropping empty values/containers.
"""

from __future__ import annotations

from collections.abc import Callable, Hashable, Iterable, Mapping, Sequence
from collections.abc import Set as AbcSet
from typing import Any, Literal


def prune_data(
    data: Any,
    keys_to_remove: Iterable[Hashable] | Callable[[Hashable], bool] | None,
    values_to_remove: Iterable[Any] | Callable[[Any], bool] | None = None,
    remove_empty: bool = False,
    *,
    max_depth: int | None = None,
) -> Any:
    """Recursively prune keys and optionally drop empty values in containers.

    Args:
        data: Root object to process (mapping/sequence/set or primitives). Not mutated.
        keys_to_remove: Keys to remove at any nesting level within mappings. Can be an
            iterable of keys or a predicate `(key) -> bool`.
        max_depth: Depth limit across containers. None means no limit; 0 means only
            the top-level container; positive values count container levels (mapping/sequence/set)
            below the root.
        remove_empty: When True, remove None, empty string, and empty containers
            (mapping/sequence/set). Values 0 and False are not treated as empty.
        values_to_remove: Values to remove anywhere. Can be an iterable of values or
            a predicate `(value) -> bool`.

    Returns:
        A new object with requested changes; container root preserves its type.

    Raises:
        ValueError: If max_depth is negative.

    Notes:
        - Depth counter increases when entering any container.
        - Container types are preserved for list/tuple/set and frozenset; mappings preserve their class
          when constructible from item pairs, otherwise fall back to dict.
        - Set elements are kept only if hashable after processing.
    """

    # Validate depth limit early
    if max_depth is not None and max_depth < 0:
        raise ValueError("max_depth cannot be negative")

    # Normalize key/value removal inputs into predicates
    def make_predicate(obj: Any, error_label: str) -> tuple[Callable[[Any], bool], bool]:
        if obj is None:
            return (lambda _x: False, True)
        if callable(obj):
            return (obj, False)
        try:
            items = list(obj)
        except TypeError as err:
            raise TypeError(f"{error_label} must be Iterable or Callable") from err
        return (lambda x: any(x == candidate for candidate in items), len(items) == 0)

    key_predicate, key_predicate_is_empty = make_predicate(keys_to_remove, error_label="keys_to_remove")
    value_predicate, value_predicate_is_empty = make_predicate(values_to_remove, error_label="values_to_remove")

    # Short-circuit: if no filters/predicates are active and remove_empty is False → return input unchanged
    if key_predicate_is_empty and value_predicate_is_empty and not remove_empty:
        return data

    def is_empty(value: Any) -> bool:
        """Return True if value should be treated as empty for cleanup.

        Rules:
        - None is empty
        - empty string is empty; non-empty string is not empty
        - empty containers (mapping/sequence/set) are empty
        - numeric zero and boolean False are not empty
        """
        if value is None:
            return True
        if isinstance(value, str):
            return len(value) == 0
        if isinstance(value, Mapping):
            return len(value) == 0
        if isinstance(value, AbcSet):
            return len(value) == 0
        if (
            isinstance(value, Sequence)
            and not isinstance(value, str)
            and not isinstance(value, bytes)
            and not isinstance(value, bytearray)
        ):
            return len(value) == 0
        return False

    def is_hashable(value: Any) -> bool:
        """Return True if value can be safely added to a set (is hashable)."""
        try:
            hash(value)
        except TypeError:
            return False
        return True

    def process(obj: Any, container_depth: int | None) -> Any:
        """Recursive kernel that processes containers according to rules.

        Depth semantics:
        - container_depth increases when entering any container (mapping/sequence/set)
        - key filtering is allowed when container_depth <= max_depth
        - recursion into children is allowed when container_depth < max_depth
        """

        # Mapping branch: filter keys if allowed; recurse into values if allowed; preserve mapping class
        if isinstance(obj, Mapping):
            # Determine whether we can filter keys and whether to recurse deeper
            can_filter = max_depth is None or (container_depth is not None and container_depth <= max_depth)
            can_recurse = max_depth is None or (container_depth is not None and container_depth < max_depth)

            result_items: list[tuple[Any, Any]] = []
            for k, v in obj.items():
                # Apply key predicate only when filtering is allowed at this depth
                if can_filter and key_predicate(k):
                    continue
                if can_recurse:
                    # Recurse into child with incremented depth
                    child = process(v, (0 if container_depth is None else container_depth) + 1)
                else:
                    # Depth limit reached; keep value as is
                    child = v
                if remove_empty and is_empty(child):
                    continue
                # Apply value predicate at mapping level only for primitives and mappings;
                # sequences/sets apply value predicate to their own elements
                is_seq_non_str = isinstance(child, Sequence) and not isinstance(child, str | bytes | bytearray)
                is_set_like = isinstance(child, AbcSet)
                if (not is_seq_non_str and not is_set_like) and value_predicate(child):
                    continue
                result_items.append((k, child))

            # Preserve mapping class when possible; otherwise fall back to dict
            try:
                if isinstance(obj, dict):
                    return dict(result_items)
                return obj.__class__(result_items)
            except Exception:
                return dict(result_items)

        # Sequence branch (list/tuple): optionally recurse into items; preserve list/tuple; filter empty items
        if (
            isinstance(obj, Sequence)
            and not isinstance(obj, str)
            and not isinstance(obj, bytes)
            and not isinstance(obj, bytearray)
        ):
            can_recurse = max_depth is None or (container_depth is not None and container_depth < max_depth)
            result_list: list[Any] = []
            for item in obj:
                if can_recurse:
                    child = process(item, (0 if container_depth is None else container_depth) + 1)
                else:
                    child = item
                if remove_empty and is_empty(child):
                    continue
                if value_predicate(child):
                    continue
                result_list.append(child)
            if isinstance(obj, tuple):
                return tuple(result_list)
            return list(result_list)

        # Set branch: optionally recurse into items (but not into set-like items themselves);
        # filter empty items; keep only hashable; preserve set/frozenset
        if isinstance(obj, AbcSet):
            can_recurse = max_depth is None or (container_depth is not None and container_depth < max_depth)
            result_set_items: list[Any] = []
            for item in obj:
                # Avoid recursing into set-like items themselves to preserve their identity
                if can_recurse and not isinstance(item, set | frozenset):
                    child = process(item, (0 if container_depth is None else container_depth) + 1)
                else:
                    child = item
                if remove_empty and is_empty(child):
                    continue
                if value_predicate(child):
                    continue
                if is_hashable(child):
                    result_set_items.append(child)
            if isinstance(obj, frozenset):
                return frozenset(result_set_items)
            return set(result_set_items)

        # Primitive or unsupported container types: return as-is
        return obj

    def empty_like(obj: Any) -> Any:
        """Return an empty container of the same kind as obj.

        Used to produce an empty root that preserves the original container type
        when `remove_empty=True` results in an empty structure.
        """
        if isinstance(obj, Mapping):
            try:
                return obj.__class__()
            except Exception:
                return {}
        if isinstance(obj, Sequence) and not isinstance(obj, str | bytes | bytearray):
            return () if isinstance(obj, tuple) else []
        if isinstance(obj, AbcSet):
            return frozenset() if isinstance(obj, frozenset) else set()
        if isinstance(obj, str):
            return ""
        return obj

    # Kick off processing with depth=0 when there is a depth limit, else no depth tracking
    root_processed = process(data, 0 if max_depth is not None else None)
    # If requested, turn an empty result into an empty container of the same type as input
    if remove_empty and is_empty(root_processed):
        return empty_like(data)
    return root_processed


def walk(
    item: Any,
    path: list[Hashable] | None = None,
    *,
    show_types: bool = False,
    quote_strings: bool = False,
    max_depth: int | None = None,
    max_items_per_container: int | None = None,
    truncate_value_len: int | None = None,
    sort_keys: bool = True,
    set_order: Literal["sorted", "stable"] = "sorted",
    show_lengths: bool = False,
    writer: Callable[[str], None] | None = None,
    style: Literal["tree"] = "tree",
) -> None:
    """Recursively walk through nested data structures and print them as a tree.

    Args:
        item: Root object to traverse (mapping/sequence/set or primitives).
        path: Current path in the structure (used internally for recursion).
        show_types: When True, show type annotations like (int), (str).
        quote_strings: When True, wrap strings in quotes and escape special characters.
        max_depth: Depth limit across containers. None means no limit.
        max_items_per_container: Maximum items to show in sequences and sets.
        truncate_value_len: Maximum length for string values before truncating with "…".
        sort_keys: When True, sort dictionary keys before display.
        set_order: Controls set element ordering ("sorted" or "stable").
        show_lengths: When True, show container sizes like [dict len=4].
        writer: Custom output function (defaults to print).
        style: Output style (currently only "tree" supported).

    Examples:
        >>> data = {"a": 1, "b": [2, 3], "c": {"d": "x"}}
        >>> walk(data, show_types=True, show_lengths=True)
        [dict len=3]
        ├─ a: 1 (int)
        ├─ b [list len=2]
        │  ├─ [0]: 2 (int)
        │  └─ [1]: 3 (int)
        └─ c [dict len=1]
           └─ d: x (str)

        >>> # More complex example with nested structures
        >>> complex_data = {
        ...     "users": [
        ...         {"id": 1, "name": "Alice", "roles": ["admin", "user"]},
        ...         {"id": 2, "name": "Bob", "roles": ["user"]}
        ...     ],
        ...     "settings": {"theme": "dark", "notifications": True}
        ... }
        >>> walk(complex_data, max_depth=2, show_lengths=True)
        [dict len=2]
        ├─ settings [dict len=2]
        └─ users [list len=2]
           ├─ [0] [dict len=3]
           └─ [1] [dict len=3]
    """
    if path is None:
        path = []
    if writer is None:
        writer = print
    _print_tree(
        item,
        path,
        prefix="",
        is_root=True,
        writer=writer,
        show_types=show_types,
        sort_keys=sort_keys,
        set_order=set_order,
        max_depth=max_depth,
        max_items=max_items_per_container,
        show_lengths=show_lengths,
        quote_strings=quote_strings,
        truncate_value_len=truncate_value_len,
    )
    return


def _is_sequence(obj: Any) -> bool:
    return isinstance(obj, Sequence) and not isinstance(obj, str | bytes | bytearray)


def _children_with_labels(
    obj: Any,
    *,
    sort_keys: bool,
    set_order: Literal["sorted", "stable"],
    max_items: int | None,
) -> list[tuple[str, Any]]:
    if isinstance(obj, Mapping):
        items = list(obj.items())
        if sort_keys:
            try:
                items = sorted(items, key=lambda kv: kv[0])
            except TypeError:
                items = sorted(items, key=lambda kv: str(kv[0]))
        # For Mapping show all elements
        return [(str(k), v) for k, v in items]
    if _is_sequence(obj):
        items_seq = list(enumerate(obj))
        if max_items is not None:
            items_seq = items_seq[:max_items]
        return [(f"[{i}]", v) for i, v in items_seq]
    if isinstance(obj, AbcSet):
        elems = list(obj)
        if set_order == "sorted":
            try:
                elems = sorted(elems)
            except TypeError:
                elems = sorted(elems, key=lambda x: str(x))
        if max_items is not None:
            elems = elems[:max_items]
        return [(f"[{i}]", v) for i, v in enumerate(elems)]
    return []


def _node_tag(obj: Any, *, show_lengths: bool) -> str:
    if isinstance(obj, Mapping):
        return "[dict]" if not show_lengths else f"[dict len={len(obj)}]"
    if _is_sequence(obj):
        return "[list]" if not show_lengths else f"[list len={len(obj)}]"
    if isinstance(obj, AbcSet):
        return "[set]" if not show_lengths else f"[set size={len(obj)}]"
    return ""


def _print_tree(
    obj: Any,
    path: list[Hashable],
    prefix: str,
    is_root: bool,
    *,
    writer: Callable[[str], None],
    show_types: bool,
    sort_keys: bool,
    set_order: Literal["sorted", "stable"],
    max_depth: int | None,
    max_items: int | None,
    show_lengths: bool,
    quote_strings: bool,
    truncate_value_len: int | None,
) -> None:
    depth = len(path)
    tag = _node_tag(obj, show_lengths=show_lengths)
    if tag:
        if is_root:
            writer(tag)
        if max_depth is not None and depth >= max_depth:
            return
        children = _children_with_labels(obj, sort_keys=sort_keys, set_order=set_order, max_items=max_items)
        for idx, (label, child) in enumerate(children):
            is_last = idx == len(children) - 1
            connector = "└─ " if is_last else "├─ "
            child_tag = _node_tag(child, show_lengths=show_lengths)
            if child_tag:
                writer(prefix + connector + f"{label} {child_tag}")
                _print_tree(
                    child,
                    [*path, label],
                    prefix + ("   " if is_last else "│  "),
                    is_root=False,
                    writer=writer,
                    show_types=show_types,
                    sort_keys=sort_keys,
                    set_order=set_order,
                    max_depth=max_depth,
                    max_items=max_items,
                    show_lengths=show_lengths,
                    quote_strings=quote_strings,
                    truncate_value_len=truncate_value_len,
                )
            else:
                rendered = _render_value(child, quote_strings=quote_strings, truncate_value_len=truncate_value_len)
                suffix = f" ({type(child).__name__})" if show_types else ""
                writer(prefix + connector + f"{label}: {rendered}{suffix}")
    else:
        rendered = _render_value(obj, quote_strings=quote_strings, truncate_value_len=truncate_value_len)
        suffix = f" ({type(obj).__name__})" if show_types else ""
        writer(str(rendered) + suffix)


def _render_value(value: Any, *, quote_strings: bool, truncate_value_len: int | None) -> str:
    if isinstance(value, str):
        text = value
        if truncate_value_len is not None and truncate_value_len >= 0 and len(text) > truncate_value_len:
            text = text[:truncate_value_len] + "…"
        if quote_strings:
            escaped = text.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'
        return text
    text = str(value)
    if truncate_value_len is not None and truncate_value_len >= 0 and len(text) > truncate_value_len:
        text = text[:truncate_value_len] + "…"
    return text


if __name__ == "__main__":
    example = {
        "a": 1,
        "e": [{"f": 3}, 4],
        "b": {"c": [10, 20, {"d": "x"}]},
        "g": {1, 2},
    }
    print("--- tree ---")
    walk(
        example,
        style="tree",
        show_types=True,
        show_lengths=True,
        max_depth=2,
        max_items_per_container=None,
        quote_strings=True,
        truncate_value_len=None,
        sort_keys=False,
        set_order="sorted",
    )
