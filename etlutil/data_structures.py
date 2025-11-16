"""Data structures utilities.

Provides `prune_data` to recursively clean common containers by removing selected keys
at any nesting level and optionally dropping empty values/containers.

Provides `walk` to recursively traverse and visualize nested data structures.

Provides `move_unknown_keys_to_extra` to normalize dictionaries by moving unknown keys
to a separate collection while preserving whitelisted keys.
"""

from __future__ import annotations

from collections.abc import Callable, Hashable, Iterable, Mapping, Sequence
from collections.abc import Set as AbcSet
from datetime import datetime
from enum import Enum
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
    print_output: bool = True,
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
) -> Any:
    """Recursively walk through nested data structures and print them as a tree.

    Always collects and returns a processed copy of the data with applied limits.
    Optionally prints the tree structure to visualize the data hierarchy.

    Args:
        item: Root object to traverse (mapping/sequence/set or primitives).
        path: Current path in the structure (used internally for recursion).
        print_output: When True, print the tree structure. When False, only return the collected object.
        show_types: When True, show type annotations like (int), (str).
        quote_strings: When True, wrap strings in quotes and escape special characters.
        max_depth: Depth limit across containers. None means no limit. When limit is reached,
            containers are replaced with empty containers of the same type.
        max_items_per_container: Maximum items to show/collect in sequences and sets.
            Does NOT apply to mappings (all keys are always processed).
        truncate_value_len: Maximum length for string values before truncating with "…".
        sort_keys: When True, sort dictionary keys before display.
        set_order: Controls set element ordering ("sorted" or "stable").
        show_lengths: When True, show container sizes like [dict len=4].
        writer: Custom output function (defaults to print).
        style: Output style (currently only "tree" supported).

    Returns:
        The collected object with applied depth and item limits. Collection behavior
        mirrors printing behavior - when max_depth is reached, nested containers
        become empty containers of the same type.

    Examples:
        >>> data = {"a": 1, "b": [2, 3], "c": {"d": "x"}}
        >>> result = walk(data, show_types=True, show_lengths=True)
        [dict len=3]
        ├─ a: 1 (int)
        ├─ b [list len=2]
        │  ├─ [0]: 2 (int)
        │  └─ [1]: 3 (int)
        └─ c [dict len=1]
           └─ d: x (str)
        >>> result
        {'a': 1, 'b': [2, 3], 'c': {'d': 'x'}}

        >>> # Collect object without printing
        >>> result = walk(data, print_output=False, max_items_per_container=2)
        >>> result
        {'a': 1, 'b': [2, 3], 'c': {'d': 'x'}}

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

    # STEP 1: Always collect processed data first
    # This creates a new data structure with applied limits (max_depth, max_items_per_container)
    # Collection behavior mirrors printing behavior for consistency
    collected_data = _collect_data(
        item,
        max_depth=max_depth,
        max_items_per_container=max_items_per_container,
        sort_keys=sort_keys,
        set_order=set_order,
    )

    # STEP 2: Optionally print tree visualization
    # Uses original data (not collected) to show full structure within limits
    # This is a separate traversal for better code clarity and testability
    if print_output:
        if writer is None:
            writer = print
        _print_tree(
            item,  # Note: uses original item, not collected_data
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

    # STEP 3: Always return the processed data structure
    # This enables programmatic use and saving to files
    return collected_data


def _collect_data(
    obj: Any,
    *,
    max_depth: int | None,
    max_items_per_container: int | None,
    sort_keys: bool,
    set_order: Literal["sorted", "stable"],
    depth: int = 0,
) -> Any:
    """Collect data from nested structures with depth and item limits."""
    # DEPTH LIMIT CHECK: Stop recursion and return empty containers
    # This mirrors the printing behavior - when max_depth is reached,
    # we show container type but not its contents
    if max_depth is not None and depth >= max_depth:
        # Return empty container of same type to preserve structure info
        if isinstance(obj, Mapping):
            return {}  # Empty dict preserves mapping structure
        elif isinstance(obj, Sequence) and not isinstance(obj, str | bytes | bytearray):
            return [] if isinstance(obj, list) else ()  # Preserve list vs tuple
        elif isinstance(obj, AbcSet):
            return set() if isinstance(obj, set) else frozenset()  # Preserve set vs frozenset
        else:
            return obj  # Primitives returned as-is

    # MAPPING BRANCH: Process all keys (ignore max_items_per_container)
    # Rationale: Dict keys are usually important metadata, unlike sequence elements
    if isinstance(obj, Mapping):
        result = {}
        # Get all children with max_items=None to process every key
        children = _children_with_labels(obj, sort_keys=sort_keys, set_order=set_order, max_items=None)
        for label, child in children:
            # Recursively process nested containers, keep primitives as-is
            if isinstance(child, Mapping | Sequence | AbcSet) and not isinstance(child, str | bytes | bytearray):
                result[label] = _collect_data(
                    child,
                    max_depth=max_depth,
                    max_items_per_container=max_items_per_container,
                    sort_keys=sort_keys,
                    set_order=set_order,
                    depth=depth + 1,  # Increment depth for nested containers
                )
            else:
                result[label] = child  # Primitives and strings copied directly
        return result

    # SEQUENCE BRANCH: Apply max_items_per_container limit
    # Unlike mappings, sequences can be safely truncated for performance/readability
    elif _is_sequence(obj):
        result_list = []
        # Apply item limit here - only process first N elements
        children = _children_with_labels(
            obj, sort_keys=sort_keys, set_order=set_order, max_items=max_items_per_container
        )
        for _, child in children:  # Note: label (index) not used in collection
            # Recursively process nested containers, keep primitives as-is
            if isinstance(child, Mapping | Sequence | AbcSet) and not isinstance(child, str | bytes | bytearray):
                result_list.append(
                    _collect_data(
                        child,
                        max_depth=max_depth,
                        max_items_per_container=max_items_per_container,
                        sort_keys=sort_keys,
                        set_order=set_order,
                        depth=depth + 1,  # Increment depth for nested containers
                    )
                )
            else:
                result_list.append(child)  # Primitives and strings copied directly

        # Preserve original sequence type: list vs tuple
        if isinstance(obj, tuple):
            return tuple(result_list)
        return result_list

    # SET BRANCH: Apply max_items_per_container limit with ordering control
    # Sets are converted to ordered list internally, then back to set/frozenset
    elif isinstance(obj, AbcSet):
        result_set_items = []
        # Apply item limit and ordering (sorted vs stable)
        children = _children_with_labels(
            obj, sort_keys=sort_keys, set_order=set_order, max_items=max_items_per_container
        )
        for _, child in children:  # Note: label (artificial index) not used in collection
            # Recursively process nested containers, keep primitives as-is
            if isinstance(child, Mapping | Sequence | AbcSet) and not isinstance(child, str | bytes | bytearray):
                result_set_items.append(
                    _collect_data(
                        child,
                        max_depth=max_depth,
                        max_items_per_container=max_items_per_container,
                        sort_keys=sort_keys,
                        set_order=set_order,
                        depth=depth + 1,  # Increment depth for nested containers
                    )
                )
            else:
                result_set_items.append(child)  # Primitives and strings copied directly

        # Preserve original set type: set vs frozenset
        if isinstance(obj, frozenset):
            return frozenset(result_set_items)
        return set(result_set_items)

    else:
        # PRIMITIVE BRANCH: Numbers, strings, None, etc.
        # Return as-is since no further processing needed
        return obj


def _is_sequence(obj: Any) -> bool:
    return isinstance(obj, Sequence) and not isinstance(obj, str | bytes | bytearray)


def _children_with_labels(
    obj: Any,
    *,
    sort_keys: bool,
    set_order: Literal["sorted", "stable"],
    max_items: int | None,
) -> list[tuple[str, Any]]:
    """Extract children from containers with display labels.

    Returns list of (label, child) pairs for tree display and collection.
    Labels are keys for mappings, [0], [1] indices for sequences/sets.
    """
    # MAPPING: Extract key-value pairs with optional sorting
    if isinstance(obj, Mapping):
        items = list(obj.items())
        if sort_keys:
            try:
                items = sorted(items, key=lambda kv: kv[0])  # Sort by key
            except TypeError:
                items = sorted(items, key=lambda kv: str(kv[0]))  # Fallback to string sort
        # Always return all mapping items (max_items ignored for mappings)
        return [(str(k), v) for k, v in items]

    # SEQUENCE: Extract indexed elements with optional limiting
    if _is_sequence(obj):
        items_seq = list(enumerate(obj))  # (index, value) pairs
        if max_items is not None:
            items_seq = items_seq[:max_items]  # Apply item limit
        return [(f"[{i}]", v) for i, v in items_seq]  # Format as [0], [1], etc.

    # SET: Convert to list with ordering and optional limiting
    if isinstance(obj, AbcSet):
        elems = list(obj)  # Convert set to list for processing
        if set_order == "sorted":
            try:
                elems = sorted(elems)  # Sort elements if possible
            except TypeError:
                elems = sorted(elems, key=lambda x: str(x))  # Fallback to string sort
        if max_items is not None:
            elems = elems[:max_items]  # Apply item limit
        return [(f"[{i}]", v) for i, v in enumerate(elems)]  # Artificial indices [0], [1], etc.

    # Non-container types have no children
    return []


def _node_tag(obj: Any, *, show_lengths: bool) -> str:
    """Generate container type tags for tree display.

    Returns tags like [dict], [list], [set] with optional length info.
    Empty string for primitives (no tag needed).
    """
    if isinstance(obj, Mapping):
        return "[dict]" if not show_lengths else f"[dict len={len(obj)}]"
    if _is_sequence(obj):
        return "[list]" if not show_lengths else f"[list len={len(obj)}]"
    if isinstance(obj, AbcSet):
        # Note: "size" for sets (not "len") to match mathematical convention
        return "[set]" if not show_lengths else f"[set size={len(obj)}]"
    return ""  # Primitives get no tag


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
    """Recursively print tree structure with ASCII art connectors."""
    depth = len(path)  # Current nesting level
    tag = _node_tag(obj, show_lengths=show_lengths)  # [dict], [list], etc.

    # CONTAINER BRANCH: Objects with children (dict, list, set)
    if tag:
        # Print container tag at root level
        if is_root:
            writer(tag)

        # DEPTH LIMIT: Stop recursion when max_depth reached
        if max_depth is not None and depth >= max_depth:
            return  # Show container tag but no contents

        # Get children with applied limits and sorting
        children = _children_with_labels(obj, sort_keys=sort_keys, set_order=set_order, max_items=max_items)

        # Print each child with appropriate tree connectors
        for idx, (label, child) in enumerate(children):
            is_last = idx == len(children) - 1
            # Tree connectors: ├─ for middle items, └─ for last item
            connector = "└─ " if is_last else "├─ "
            child_tag = _node_tag(child, show_lengths=show_lengths)

            # NESTED CONTAINER: Child has its own children
            if child_tag:
                writer(prefix + connector + f"{label} {child_tag}")
                # Recursive call with updated path and prefix
                _print_tree(
                    child,
                    [*path, label],  # Extend path with current label
                    prefix + ("   " if is_last else "│  "),  # Adjust prefix for tree lines
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
            # PRIMITIVE VALUE: Child is a leaf node
            else:
                rendered = _render_value(child, quote_strings=quote_strings, truncate_value_len=truncate_value_len)
                suffix = f" ({type(child).__name__})" if show_types else ""
                writer(prefix + connector + f"{label}: {rendered}{suffix}")

    # PRIMITIVE BRANCH: Root object is a primitive (number, string, etc.)
    else:
        rendered = _render_value(obj, quote_strings=quote_strings, truncate_value_len=truncate_value_len)
        suffix = f" ({type(obj).__name__})" if show_types else ""
        writer(str(rendered) + suffix)


def _render_value(value: Any, *, quote_strings: bool, truncate_value_len: int | None) -> str:
    """Format primitive values for tree display.

    Handles string escaping, quoting, and length truncation.
    Used for leaf nodes (non-container values) in the tree.

    Examples:
        >>> _render_value("hello world", quote_strings=False, truncate_value_len=None)
        'hello world'

        >>> _render_value("hello world", quote_strings=True, truncate_value_len=None)
        '"hello world"'

        >>> _render_value("hello world", quote_strings=False, truncate_value_len=5)
        'hello…'

        >>> _render_value('text with "quotes"', quote_strings=True, truncate_value_len=None)
        '"text with \\"quotes\\""'

        >>> _render_value(42, quote_strings=False, truncate_value_len=None)
        '42'

        >>> _render_value([1, 2, 3, 4, 5], quote_strings=False, truncate_value_len=8)
        '[1, 2, 3…'

        >>> _render_value(True, quote_strings=False, truncate_value_len=None)
        'True'
    """
    # STRING HANDLING: Special processing for string values
    if isinstance(value, str):
        text = value
        # Truncate long strings with ellipsis
        if truncate_value_len is not None and truncate_value_len >= 0 and len(text) > truncate_value_len:
            text = text[:truncate_value_len] + "…"
        # Add quotes and escape special characters if requested
        if quote_strings:
            escaped = text.replace("\\", "\\\\").replace('"', '\\"')  # Escape backslashes and quotes
            return f'"{escaped}"'
        return text

    # NON-STRING HANDLING: Convert to string representation
    text = str(value)  # Convert any type to string (int, bool, None, etc.)
    # Truncate long representations (e.g., long lists, large numbers)
    if truncate_value_len is not None and truncate_value_len >= 0 and len(text) > truncate_value_len:
        text = text[:truncate_value_len] + "…"
    return text


def move_unknown_keys_to_extra(
    data: dict,
    allowed_keys: Iterable[Hashable],
    *,
    extra_key: str = "extra_collected",
    always_add_extra: bool = False,
) -> tuple[dict, list[str]]:
    """Move unknown keys from dict to extra collection, keeping only whitelisted keys.

    Args:
        data: Input dictionary to normalize. Must be a dict.
        allowed_keys: Iterable of allowed keys (whitelist). All keys converted to str.
        extra_key: Key name for collecting extra items. Defaults to "extra_collected".
        always_add_extra: If True, always add extra_key even when no keys were moved.
            Defaults to False (only add extra_key when there are moved keys).

    Returns:
        Tuple of (normalized_dict, moved_keys_list).
        - normalized_dict: New dict with whitelisted keys + extra_key if needed.
        - moved_keys_list: List of final key names that were moved to extra.

    Key collision rules:
        - All keys normalized to str() for processing
        - If multiple keys stringify to same name:
          - String key keeps bare name (e.g., '1' stays '1')
          - Non-string keys get type suffix (e.g., 1 → '1__int')
          - If no string key exists, all get suffixes

    Extra key collision handling:
        - If extra_key exists in input, rename to f'{extra_key}_original'
        - Cascade with _original2, _original3, etc. until free name found

    Output sorting:
        - All keys sorted lexicographically by final string names
        - Both top-level and extra_collected contents sorted

        Examples:
        >>> data = {"id": 123, "name": "alex", "age": 30, "city": "berlin"}
        >>> result, moved = move_unknown_keys_to_extra(data, ["id", "name"])
        >>> result
        {'extra_collected': {'age': 30, 'city': 'berlin'}, 'id': 123, 'name': 'alex'}
        >>> moved
        ['age', 'city']

        >>> # Always add extra_collected even when no keys moved
        >>> data = {"id": 123, "name": "alex"}
        >>> result, moved = move_unknown_keys_to_extra(data, ["id", "name"], always_add_extra=True)
        >>> result
        {'extra_collected': {}, 'id': 123, 'name': 'alex'}
        >>> moved
        []

        >>> # Key collision example
        >>> data = {"1": "str_val", 1: "int_val"}
        >>> result, moved = move_unknown_keys_to_extra(data, ["1"])
        >>> result
        {'1': 'str_val', 'extra_collected': {'1__int': 'int_val'}}
        >>> moved
        ['1__int']
    """
    if not isinstance(data, dict):
        raise TypeError("data must be a dict")

    # Normalize allowed_keys to set of strings for consistent comparison
    # Handle None input gracefully by treating as empty whitelist
    allowed_str_keys = {str(k) for k in allowed_keys} if allowed_keys is not None else set()

    # Step 1: Resolve key collisions after str() conversion
    # This handles cases where different key types stringify to same name (e.g., 1 and "1")
    resolved_keys = _resolve_key_collisions(data)

    # Step 2: Handle extra_key collision BEFORE classification
    # If extra_key already exists in data, we need to rename it to avoid overwriting
    # Track renamed keys so they are kept on top level regardless of whitelist
    renamed_keys: set[str] = set()

    # Check if extra_key conflicts with any resolved key
    if extra_key in resolved_keys:
        # Rename the conflicting key to avoid collision with our collection key
        conflicting_value = resolved_keys.pop(extra_key)
        new_key = _resolve_extra_key_collision(resolved_keys, f"{extra_key}_original")
        resolved_keys[new_key] = conflicting_value
        renamed_keys.add(new_key)

    # Also handle cascade collisions with _original variants
    # This ensures that if data has "extra_collected_original", it gets renamed too
    keys_to_rename = []
    for key in resolved_keys:
        if key.startswith(f"{extra_key}_original"):
            keys_to_rename.append(key)

    # Rename all conflicting _original variants to avoid nested conflicts
    for key in keys_to_rename:
        value = resolved_keys.pop(key)
        new_key = _resolve_extra_key_collision(resolved_keys, key)
        resolved_keys[new_key] = value
        renamed_keys.add(new_key)

    # Step 3: Classify keys into kept vs extra based on whitelist
    kept_items: dict[str, Any] = {}
    extra_items: dict[str, Any] = {}
    moved_keys: list[str] = []

    for final_key, original_value in resolved_keys.items():
        # Renamed keys are always kept on top level, regardless of whitelist
        # This preserves original data that had conflicting names with extra_key
        if final_key in allowed_str_keys or final_key in renamed_keys:
            kept_items[final_key] = original_value
        else:
            # Keys not in whitelist go to extra collection
            extra_items[final_key] = original_value
            moved_keys.append(final_key)

    # Step 4: Add extra items under extra_key if needed
    # Create extra collection if there are items OR if always_add_extra is True
    if (extra_items or always_add_extra) and extra_key is not None:
        kept_items[extra_key] = extra_items

    # Step 5: Sort all keys lexicographically for consistent output
    # This ensures deterministic results regardless of input dict order
    result = {k: kept_items[k] for k in sorted(kept_items.keys())}

    # Sort extra_collected contents too for consistency
    if extra_key in result and isinstance(result[extra_key], dict):
        result[extra_key] = {k: result[extra_key][k] for k in sorted(result[extra_key].keys())}

    return result, sorted(moved_keys)


def _resolve_key_collisions(data: dict) -> dict[str, Any]:
    """Resolve key name collisions after str() conversion.

    Key collision resolution logic:
    1. Convert all keys to strings using str() - this can cause collisions
       e.g., int(1), float(1.0), Decimal('1') all become '1'
    2. Group original keys by their string representation
    3. For each collision group:
       - If there's a string key: it keeps the "bare" name (e.g., '1')
       - All non-string keys get type suffix (e.g., '1__int', '1__decimal')
       - If no string key exists: all keys get type suffixes
    4. Process keys in deterministic order to ensure stable results
       - Sort by string representation first
       - Then by type priority (str first, then others alphabetically)

    Examples:
        {'1': 'str_val', 1: 'int_val'} → {'1': 'str_val', '1__int': 'int_val'}
        {1: 'int_val', 1.0: 'float_val'} → {'1__int': 'int_val', '1__float': 'float_val'}

    Returns:
        dict mapping final_key -> original_value
    """
    # Group keys by their str() representation, maintaining insertion order
    str_groups: dict[str, list[tuple[Any, Any]]] = {}  # str_name -> [(original_key, value), ...]

    # Process in deterministic order to ensure stable collision resolution
    # Sort by: 1) string representation, 2) type priority (str first), 3) type name
    items = list(data.items())
    items.sort(key=lambda kv: (str(kv[0]), 0 if isinstance(kv[0], str) else 1, type(kv[0]).__name__))

    # Build collision groups by grouping keys with same str() representation
    for original_key, value in items:
        str_name = str(original_key)
        if str_name not in str_groups:
            str_groups[str_name] = []
        str_groups[str_name].append((original_key, value))

    resolved: dict[str, Any] = {}

    # Process each collision group and apply resolution rules
    for str_name, key_value_pairs in str_groups.items():
        if len(key_value_pairs) == 1:
            # No collision - use str_name as-is
            original_key, value = key_value_pairs[0]
            resolved[str_name] = value
        else:
            # Collision detected - apply priority-based resolution
            string_key_pair = None
            non_string_pairs = []

            # Separate string keys from non-string keys
            for original_key, value in key_value_pairs:
                if isinstance(original_key, str):
                    if string_key_pair is None:  # Take first string key if multiple
                        string_key_pair = (original_key, value)
                    else:
                        # Multiple string keys with same str() - shouldn't happen but handle gracefully
                        non_string_pairs.append((original_key, value))
                else:
                    non_string_pairs.append((original_key, value))

            # Apply collision resolution rules based on string key presence
            if string_key_pair is not None:
                # String key gets bare name (highest priority)
                _, value = string_key_pair
                resolved[str_name] = value

                # Non-string keys get type suffixes to avoid collision
                for original_key, value in non_string_pairs:
                    type_name = original_key.__class__.__name__.lower()
                    suffixed_name = f"{str_name}__{type_name}"
                    resolved[suffixed_name] = value
            else:
                # No string key - all keys get type suffixes (no "bare" owner)
                for original_key, value in key_value_pairs:
                    type_name = original_key.__class__.__name__.lower()
                    suffixed_name = f"{str_name}__{type_name}"
                    resolved[suffixed_name] = value

    return resolved


def _resolve_extra_key_collision(kept_items: dict[str, Any], base_key: str) -> str:
    """Find a free name for base_key by cascading _original suffixes.

    When extra_key conflicts with existing data, this function finds a safe alternative
    name by trying _original, _original2, _original3, etc. until a free name is found.

    Args:
        kept_items: Dictionary to check for name conflicts
        base_key: Preferred key name that might conflict

    Returns:
        A free key name that doesn't conflict with kept_items
    """
    # If no conflict, use base_key as-is
    if base_key not in kept_items:
        return base_key

    # Find first available _original variant
    counter = 1
    while True:
        suffix = "_original" if counter == 1 else f"_original{counter}"
        candidate = f"{base_key}{suffix}"
        if candidate not in kept_items:
            return candidate
        counter += 1


class ConvertType(Enum):
    """
    Supported conversion types for convert_dict_types function.

    Provides type-safe enum values for better IDE support and reduced typos.
    Each enum value corresponds to a string type name used internally.
    """

    INT = "int"  # Convert to Python int
    FLOAT = "float"  # Convert to Python float
    BOOL = "bool"  # Convert to Python bool
    DATE = "date"  # Convert to datetime.date object
    DATETIME = "datetime"  # Convert to datetime.datetime object
    TIMESTAMP = "timestamp"  # Convert unix timestamp to datetime object
    TIMESTAMP_TO_ISO = "timestamp_to_iso"  # Convert unix timestamp to ISO string
    TIMESTAMP_TO_ISO_DATE = "timestamp_to_iso_date"  # Convert unix timestamp to ISO date (YYYY-MM-DD)
    TIMESTAMP_TO_ISO_YYYY_MM = "timestamp_to_iso_YYYY-MM"  # Convert unix timestamp to YYYY-MM format
    TIMESTAMP_TO_ISO_YYYY = "timestamp_to_iso_YYYY"  # Convert unix timestamp to YYYY format
    STR = "str"  # Convert to Python str


def convert_dict_types(
    data: dict[str, Any] | list[Any],
    type_schema: dict[str, str | ConvertType],
    recursive: bool = False,
    strict: bool = False,
    empty_string_to_none: bool = False,
    datetime_formats: list[str] | None = None,
) -> dict[str, Any] | list[Any]:
    """
    Convert dictionary/list values to specified types based on schema.

    This function is essential for ETL workflows where data comes with mixed types
    (often strings from APIs/CSVs) and needs to be converted to proper Python types
    for analysis or storage.

    Args:
        data: Input dictionary or list with mixed values
        type_schema: Dictionary mapping field names to type names or ConvertType enums.
                    Supported types: "int", "float", "bool", "date", "datetime",
                    "timestamp", "timestamp_to_iso", "timestamp_to_iso_date",
                    "timestamp_to_iso_YYYY-MM", "timestamp_to_iso_YYYY", "str"
        recursive: If True, recursively process nested dictionaries and lists.
                  Only processes dict and list containers, not tuples or other types.
        strict: If True, raise exceptions on conversion errors instead of returning
               original value. Use for data validation.
        empty_string_to_none: If True, convert empty strings to None before type conversion.
                             Useful when empty strings should be treated as missing values.
        datetime_formats: Custom datetime formats to try in order. If None, uses:
                         ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]

    Returns:
        Dictionary/list with converted values. Original structure is preserved,
        only values matching the schema are converted.

    Raises:
        ValueError: In strict mode when conversion fails (e.g., "abc" -> int)
        TypeError: In strict mode when conversion fails

    Examples:
        >>> data = {"count": "42", "price": "3.14", "active": "true"}
        >>> schema = {"count": "int", "price": "float", "active": "bool"}
        >>> convert_dict_types(data, schema)
        {"count": 42, "price": 3.14, "active": True}

        >>> # Unix timestamp conversion
        >>> data = {"created": "1735056631"}
        >>> schema = {"created": "timestamp_to_iso"}
        >>> convert_dict_types(data, schema)
        {"created": "2024-12-24T20:10:31"}

        >>> # Recursive processing of nested data
        >>> data = {"items": [{"value": "100"}, {"value": "200"}]}
        >>> schema = {"value": "int"}
        >>> convert_dict_types(data, schema, recursive=True)
        {"items": [{"value": 100}, {"value": 200}]}
    """
    # Set default datetime formats if none provided
    if datetime_formats is None:
        datetime_formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]

    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            # Recursively process nested containers if requested
            if recursive and isinstance(value, dict | list):
                result[key] = convert_dict_types(
                    value, type_schema, recursive, strict, empty_string_to_none, datetime_formats
                )
            else:
                # Convert value if key is in schema, otherwise keep as-is
                result[key] = _convert_value_if_needed(
                    key, value, type_schema, strict, empty_string_to_none, datetime_formats
                )
        return result
    elif isinstance(data, list):
        if recursive:
            # Process each list item recursively
            return [
                convert_dict_types(item, type_schema, recursive, strict, empty_string_to_none, datetime_formats)
                for item in data
            ]
        else:
            # Non-recursive: return list unchanged
            return data
    else:
        # Not a dict or list: return unchanged
        return data


def _convert_value_if_needed(
    key: str,
    value: Any,
    type_schema: dict[str, str | ConvertType],
    strict: bool,
    empty_string_to_none: bool,
    datetime_formats: list[str],
) -> Any:
    """Convert value if key exists in schema, otherwise return unchanged."""
    if key not in type_schema:
        return value

    # Extract string type name from enum if needed
    target_type = type_schema[key]
    if isinstance(target_type, ConvertType):
        target_type = target_type.value

    return _convert_value(value, target_type, strict, empty_string_to_none, datetime_formats)


def _convert_value(
    value: Any, target_type: str, strict: bool, empty_string_to_none: bool, datetime_formats: list[str]
) -> Any:
    """
    Convert single value to target type.

    Core conversion logic that handles all supported type transformations.
    In non-strict mode, returns original value if conversion fails.
    """
    # None values are always preserved
    if value is None:
        return value

    # Handle empty string conversion
    if empty_string_to_none and value == "":
        return None
    elif not empty_string_to_none and value == "":
        return value

    def handle_error(exc: Exception) -> Any:
        """Handle conversion errors based on strict mode."""
        if strict:
            raise exc
        return value

    try:
        if target_type == "int":
            # Handle boolean to int conversion first (True->1, False->0)
            if isinstance(value, bool):
                return int(value)
            # Handle string numbers that may have decimal points
            if isinstance(value, str) and value.replace(".", "", 1).replace("-", "", 1).isdigit():
                return int(float(value))  # Convert via float to handle "3.14" -> 3
            if isinstance(value, int | float):
                return int(value)
            return int(value)  # Fallback for other types

        elif target_type == "float":
            if isinstance(value, bool):
                return float(value)
            if isinstance(value, int | float | str):
                return float(value)
            return float(value)

        elif target_type == "bool":
            # String boolean conversion with common true/false representations
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes", "on")
            # Numeric boolean conversion (0 is False, everything else is True)
            if isinstance(value, int | float):
                return bool(value)
            return bool(value)

        elif target_type == "date":
            # Parse ISO date strings (YYYY-MM-DD)
            if isinstance(value, str):
                return datetime.strptime(value, "%Y-%m-%d").date()
            return value

        elif target_type == "datetime":
            # Try multiple datetime formats in order
            if isinstance(value, str):
                for fmt in datetime_formats:
                    try:
                        return datetime.strptime(value, fmt)
                    except ValueError:
                        continue
                raise ValueError(f"Unable to parse datetime: {value}")
            return value

        elif target_type == "timestamp":
            # Convert unix timestamp to datetime object
            if isinstance(value, str | int | float):
                timestamp = float(value)
                return datetime.fromtimestamp(timestamp)
            return value

        elif target_type == "timestamp_to_iso":
            # Convert unix timestamp to ISO string format
            if isinstance(value, str | int | float):
                timestamp = float(value)
                dt = datetime.fromtimestamp(timestamp)
                return dt.isoformat()
            return value

        elif target_type == "timestamp_to_iso_date":
            # Convert unix timestamp to ISO date (YYYY-MM-DD)
            if isinstance(value, str | int | float):
                timestamp = float(value)
                dt = datetime.fromtimestamp(timestamp)
                return dt.strftime("%Y-%m-%d")
            return value

        elif target_type == "timestamp_to_iso_YYYY-MM":
            # Convert unix timestamp to YYYY-MM format
            if isinstance(value, str | int | float):
                timestamp = float(value)
                dt = datetime.fromtimestamp(timestamp)
                return dt.strftime("%Y-%m")
            return value

        elif target_type == "timestamp_to_iso_YYYY":
            # Convert unix timestamp to YYYY format
            if isinstance(value, str | int | float):
                timestamp = float(value)
                dt = datetime.fromtimestamp(timestamp)
                return dt.strftime("%Y")
            return value

        else:  # str or unknown type
            # Default: convert to string
            return str(value)

    except (ValueError, TypeError) as e:
        return handle_error(e)
