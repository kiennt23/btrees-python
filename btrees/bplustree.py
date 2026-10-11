from btrees._display import render_tree


_MISSING_VALUE = object()


class BPlusNode:
    def __init__(self, leaf=False):
        self.leaf = leaf
        self.keys = []
        self.children = []
        self.next: BPlusNode | None = None


# assumption: equal key routes to the right
# left is inclusive, right is exclusive
class BPlusTree:
    def __init__(self, t: int) -> None:
        if t < 1:
            raise ValueError("t must be greater than or equal to 1")

        if isinstance(t, bool) or not isinstance(t, int):
            raise TypeError("t must be an integer")

        self.t = t
        self.max_keys = 2 * t - 1
        self.min_keys = t - 1
        self.root = BPlusNode(leaf=True)

    def display(self) -> None:
        print(render_tree(self.root))

    # remember len(self.children) == len(self.keys) + 1
    def search(self, key, node=None):
        if node is None:
            node = self.root

        i = 0
        while i < len(node.keys) and key > node.keys[i]:
            i += 1

        if node.leaf:
            if i < len(node.keys) and key == node.keys[i]:
                return node.children[i]
            return None
        else:
            if i < len(node.keys) and key == node.keys[i]:
                return self.search(key, node.children[i + 1])

            return self.search(key, node.children[i])

    def search_range(self, start, end, node: BPlusNode | None = None):
        if start > end:
            raise ValueError("start must be less than or equal to end")

        if node is None:
            node = self.root
        result = []
        i = 0
        while i < len(node.keys) and start > node.keys[i]:
            i += 1

        if node.leaf:
            current: BPlusNode | None = node

            while current is not None:
                while i < len(current.keys):
                    if end <= current.keys[i]:
                        return result

                    result.append(current.children[i])
                    i += 1

                current = current.next
                i = 0

            return result

        else:
            if i < len(node.keys):
                return self.search_range(start, end, node.children[i + 1])

            return self.search_range(start, end, node.children[i])

    def insert(self, key, value=_MISSING_VALUE):
        if value is _MISSING_VALUE:
            value = key

        root = self.root
        # find the place to insert
        if len(root.keys) == self.max_keys:
            new_root = BPlusNode(leaf=False)
            self.root = new_root
            new_root.children.append(root)
            self._split_children(new_root, 0, root)
            self._insert_non_full(new_root, key, value)
        else:
            self._insert_non_full(root, key, value)

    def _insert_non_full(self, node, key, value):
        if node.leaf:
            idx = 0
            while idx < len(node.keys) and key > node.keys[idx]:
                idx += 1

            node.keys.insert(idx, key)
            node.children.insert(idx, value)
        else:
            idx = 0
            while idx < len(node.keys) and key >= node.keys[idx]:
                idx += 1

            child = node.children[idx]
            if len(child.keys) == self.max_keys:
                self._split_children(node, idx, child)
                if key >= node.keys[idx]:
                    idx += 1

            self._insert_non_full(node.children[idx], key, value)

    # the assumption is that source is full
    def _split_children(self, target: BPlusNode, pos: int, source: BPlusNode):
        min_keys = self.min_keys
        max_keys = self.max_keys
        # source is left
        right = BPlusNode(leaf=source.leaf)
        target.children.insert(pos + 1, right)

        # split position: t - 1
        if source.leaf:
            target.keys.insert(pos, source.keys[min_keys])
            right.keys = source.keys[
                min_keys:max_keys
            ]  # the assumption is that target is full
            source.keys = source.keys[0:min_keys]
            right.children = source.children[min_keys:max_keys]
            source.children = source.children[0:min_keys]
            right.next = source.next
            source.next = right
        else:
            target.keys.insert(pos, source.keys[min_keys])
            right.keys = source.keys[min_keys + 1 : max_keys]
            source.keys = source.keys[0:min_keys]
            right.children = source.children[min_keys + 1 : max_keys + 1]
            source.children = source.children[0 : min_keys + 1]

    def delete(self, key):
        self._delete_recursive(self.root, key)
        # remove empty root
        if not self.root.leaf and len(self.root.keys) == 0:
            self.root = self.root.children[0]

    def _delete_recursive(self, node, key):
        if node.leaf:
            if key in node.keys:
                idx = node.keys.index(key)
                node.keys.pop(idx)
                node.children.pop(idx)

            return

        idx = 0
        while idx < len(node.keys) and key >= node.keys[idx]:
            idx += 1

        child = node.children[idx]
        self._delete_recursive(child, key)

        if len(child.keys) < self.min_keys:
            self._handle_underflow(node, idx)

    def _handle_underflow(self, parent, pos):
        left_sibling = parent.children[pos - 1] if pos > 0 else None
        right_sibling = (
            parent.children[pos + 1] if pos < len(parent.children) - 1 else None
        )
        this_sibling = parent.children[pos]

        # borrow from left
        if left_sibling and len(left_sibling.keys) > self.min_keys:
            if this_sibling.leaf:
                this_sibling.keys.insert(0, left_sibling.keys.pop())
                this_sibling.children.insert(0, left_sibling.children.pop())
                parent.keys[pos - 1] = this_sibling.keys[0]
            else:
                this_sibling.keys.insert(0, parent.keys[pos - 1])
                parent.keys[pos - 1] = left_sibling.keys.pop()
                this_sibling.children.insert(0, left_sibling.children.pop())

        # borrow from right
        elif right_sibling and len(right_sibling.keys) > self.min_keys:
            if this_sibling.leaf:
                this_sibling.keys.append(right_sibling.keys.pop(0))
                this_sibling.children.append(right_sibling.children.pop(0))
                parent.keys[pos] = right_sibling.keys[0]
            else:
                this_sibling.keys.append(parent.keys[pos])
                parent.keys[pos] = right_sibling.keys.pop(0)
                this_sibling.children.append(right_sibling.children.pop(0))

        # merge
        else:
            if left_sibling:
                if this_sibling.leaf:
                    left_sibling.keys.extend(this_sibling.keys)
                    left_sibling.children.extend(this_sibling.children)
                    left_sibling.next = this_sibling.next
                else:
                    left_sibling.keys.append(parent.keys[pos - 1])
                    left_sibling.keys.extend(this_sibling.keys)
                    left_sibling.children.extend(this_sibling.children)

                parent.keys.pop(pos - 1)
                parent.children.pop(pos)

            elif right_sibling:
                if this_sibling.leaf:
                    this_sibling.keys.extend(right_sibling.keys)
                    this_sibling.children.extend(right_sibling.children)
                    this_sibling.next = right_sibling.next
                else:
                    this_sibling.keys.append(parent.keys[pos])
                    this_sibling.keys.extend(right_sibling.keys)
                    this_sibling.children.extend(right_sibling.children)

                parent.keys.pop(pos)
                parent.children.pop(pos + 1)
