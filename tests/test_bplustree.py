import random
from collections import Counter
from typing import Any, cast

import pytest

from btrees.bplustree import BPlusNode, BPlusTree


def build_tree(
    entries: list[tuple[int, Any]],
    *,
    degree: int = 2,
) -> BPlusTree:
    tree = BPlusTree(degree)
    for key, value in entries:
        tree.insert(key, value)
    tree.display()
    return tree


def leaf_items(tree: BPlusTree) -> list[tuple[Any, Any]]:
    node = tree.root
    while not node.leaf:
        node = node.children[0]

    items: list[tuple[Any, Any]] = []
    seen: set[int] = set()
    current: BPlusNode | None = node
    while current is not None:
        assert id(current) not in seen, "leaf chain contains a cycle"
        seen.add(id(current))
        assert len(current.keys) == len(current.children)
        items.extend(zip(current.keys, current.children, strict=True))
        current = current.next

    return items


def assert_structure(node: BPlusNode) -> None:
    assert node.keys == sorted(node.keys)
    if node.leaf:
        assert len(node.children) == len(node.keys)
        return

    assert len(node.children) == len(node.keys) + 1
    for child in node.children:
        assert isinstance(child, BPlusNode)
        assert_structure(child)


@pytest.mark.parametrize("degree", [0, -1])
def test_constructor_rejects_degree_below_one(degree: int) -> None:
    with pytest.raises(ValueError):
        BPlusTree(degree)


@pytest.mark.parametrize("degree", [True, 1.5, "2", None])
def test_constructor_rejects_non_integer_degree(degree: object) -> None:
    with pytest.raises(TypeError):
        BPlusTree(cast(Any, degree))


def test_constructor_accepts_degree_one() -> None:
    tree = BPlusTree(1)

    assert tree.root.leaf
    assert tree.root.keys == []


def test_display_empty_tree(capsys: pytest.CaptureFixture[str]) -> None:
    tree = BPlusTree(2)

    tree.display()

    output = capsys.readouterr().out
    assert "┌───────┐\n│ empty │──→ ∅\n└───────┘" in output


def test_display_split_tree(capsys: pytest.CaptureFixture[str]) -> None:
    tree = build_tree([(key, f"value-{key}") for key in range(1, 5)])

    tree.display()

    output = capsys.readouterr().out
    diagram = output.split("\n\n", 1)[1].splitlines()
    assert diagram[1].count("●") == 2
    assert "│ 2 │" in diagram[1]
    assert "│ 1 │────→│ 2 │ 3 │ 4 │──→ ∅" in output
    for column, character in enumerate(diagram[1]):
        if character == "●":
            assert diagram[3][column] == "▼"
            assert diagram[4][column] == "─"


def test_insert_and_search_shuffled_unique_keys() -> None:
    keys = list(range(100))
    random.Random(42).shuffle(keys)
    tree = build_tree([(key, f"value-{key}") for key in keys], degree=3)

    for key in range(100):
        assert tree.search(key) == f"value-{key}"

    assert tree.search(-1) is None
    assert tree.search(100) is None
    assert_structure(tree.root)


def test_insert_without_value_uses_key_as_value() -> None:
    tree = BPlusTree(2)

    tree.insert(7)

    assert tree.search(7) == 7


@pytest.mark.parametrize("value", [None, False, 0, ""])
def test_insert_preserves_explicit_falsey_values(value: object) -> None:
    tree = BPlusTree(2)

    tree.insert(1, value)

    assert tree.search_range(1, 2) == [value]


def test_leaf_chain_contains_every_inserted_item_in_key_order() -> None:
    keys = list(range(75))
    random.Random(7).shuffle(keys)
    tree = build_tree([(key, f"value-{key}") for key in keys], degree=3)

    assert leaf_items(tree) == [(key, f"value-{key}") for key in range(75)]


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        (-5, 0, []),
        (-5, 2, ["value-0", "value-1"]),
        (2, 5, ["value-2", "value-3", "value-4"]),
        (5, 6, ["value-5"]),
        (10, 20, ["value-10", "value-11"]),
        (12, 20, []),
    ],
)
def test_search_range_uses_left_inclusive_right_exclusive_bounds(
    start: int,
    end: int,
    expected: list[str],
) -> None:
    tree = build_tree(
        [(key, f"value-{key}") for key in range(12)],
        degree=2,
    )

    assert tree.search_range(start, end) == expected


def test_search_range_supports_empty_interval() -> None:
    tree = build_tree([(key, key) for key in range(10)])

    assert tree.search_range(5, 5) == []


def test_search_range_rejects_reversed_interval() -> None:
    tree = build_tree([(1, "one")])

    with pytest.raises(ValueError, match="start must be less than or equal to end"):
        tree.search_range(2, 1)


@pytest.mark.parametrize("degree", [2, 3, 5])
def test_search_range_matches_reference_model(degree: int) -> None:
    keys = list(range(30))
    random.Random(91).shuffle(keys)
    tree = build_tree([(key, key) for key in keys], degree=degree)

    for start in range(-2, 31):
        for end in range(start, 33):
            expected = [key for key in range(30) if start <= key < end]
            assert tree.search_range(start, end) == expected


def test_search_range_returns_duplicates_split_across_leaves() -> None:
    tree = build_tree([(5, value) for value in range(20)], degree=2)

    assert Counter(tree.search_range(5, 6)) == Counter(range(20))


def test_delete_existing_and_missing_keys() -> None:
    tree = build_tree([(key, f"value-{key}") for key in range(20)])

    tree.delete(7)
    tree.delete(100)

    assert tree.search(7) is None
    assert leaf_items(tree) == [(key, f"value-{key}") for key in range(20) if key != 7]
    assert_structure(tree.root)


def test_delete_removes_one_duplicate_at_a_time() -> None:
    tree = build_tree([(5, value) for value in range(8)], degree=2)

    before = Counter(value for key, value in leaf_items(tree) if key == 5)
    tree.delete(5)
    after = Counter(value for key, value in leaf_items(tree) if key == 5)

    assert sum(after.values()) == sum(before.values()) - 1
    assert after <= before


@pytest.mark.parametrize("degree", [2, 3, 4])
def test_randomized_deletion_preserves_remaining_values(degree: int) -> None:
    keys = list(range(60))
    insertion_order = keys.copy()
    deletion_order = keys.copy()
    random.Random(101).shuffle(insertion_order)
    random.Random(202).shuffle(deletion_order)
    tree = build_tree([(key, f"value-{key}") for key in insertion_order], degree=degree)
    remaining = set(keys)

    for deleted in deletion_order:
        tree.delete(deleted)
        remaining.remove(deleted)
        assert tree.search(deleted) is None
        assert leaf_items(tree) == [(key, f"value-{key}") for key in sorted(remaining)]
        assert_structure(tree.root)

    assert tree.root.leaf
    assert tree.root.keys == []
    assert tree.root.children == []
    assert tree.root.next is None
