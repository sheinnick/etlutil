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
