from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from btrees.bplustree import BPlusNode


def render_tree(root: BPlusNode) -> str:
    """Lay out subtrees so each child pointer sits above its destination."""
    widths: dict[BPlusNode, int] = {}
    leaf_boxes: dict[BPlusNode, tuple[str, str, str]] = {}

    def measure(node: BPlusNode) -> int:
        if node.leaf:
            cells = [ascii(key) for key in node.keys] or ["empty"]
            borders = ["─" * (len(cell) + 2) for cell in cells]
            box = (
                "┌" + "┬".join(borders) + "┐",
                "│ " + " │ ".join(cells) + " │",
                "└" + "┴".join(borders) + "┘",
            )
            leaf_boxes[node] = box
            width = len(box[0])
        else:
            width = sum(measure(child) for child in node.children)
            width += sum(len(ascii(key)) + 4 for key in node.keys)
        widths[node] = width
        return width

    measure(root)
    rows: list[list[str]] = []
    leaves: list[tuple[BPlusNode, int, int]] = []

    def put(y: int, x: int, text: str) -> None:
        while len(rows) <= y:
            rows.append([])
        row = rows[y]
        row.extend(" " for _ in range(x + len(text) - len(row)))
        row[x : x + len(text)] = text

    def draw(node: BPlusNode, x: int, y: int) -> None:
        width = widths[node]
        if node.leaf:
            for offset, line in enumerate(leaf_boxes[node]):
                put(y + offset, x, line)
            leaves.append((node, x, y))
            return

        top = list("┌" + "─" * (width - 2) + "┐")
        middle = list("│" + " " * (width - 2) + "│")
        bottom = list("└" + "─" * (width - 2) + "┘")
        offset = 0
        for index, child in enumerate(node.children):
            pointer = offset + widths[child] // 2
            middle[pointer] = "●"
            bottom[pointer] = "┬"
            put(y + 3, x + pointer, "▼")
            draw(child, x + offset, y + 4)
            offset += widths[child]
            if index < len(node.keys):
                key = ascii(node.keys[index])
                left = offset
                right = left + len(key) + 3
                for boundary in (left, right):
                    top[boundary] = "┬"
                    middle[boundary] = "│"
                    bottom[boundary] = "┴"
                middle[left + 2 : left + 2 + len(key)] = key
                offset += len(key) + 4
        for offset, line in enumerate((top, middle, bottom)):
            put(y + offset, x, "".join(line))

    draw(root, 0, 0)
    positions = {node: (x, y) for node, x, y in leaves}
    for node, x, y in leaves:
        end = x + widths[node]
        if node.next is None:
            put(y + 1, end, "──→ ∅")
        else:
            next_x, _ = positions[node.next]
            put(y + 1, end, "─" * (next_x - end - 1) + "→")

    legend = "● = child pointer; internal keys = separators; leaf arrows = next (∅ = end)."
    return legend + "\n\n" + "\n".join("".join(row).rstrip() for row in rows)
