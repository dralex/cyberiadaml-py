# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The hierarchical tree geometry types (a port of libhtreegeom)
#
# Copyright (C) 2026 Alexey Fedoseev <aleksey@fedoseev.net>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see https://www.gnu.org/licenses/
#
# -----------------------------------------------------------------------------
"""The types and constants of the hierarchical tree geometry."""
import math
import struct
from typing import List, Optional

# the coordinate formats
COORD_NONE = 0
COORD_ABSOLUTE = 1          # absolute coordinates
COORD_LEFT_TOP = 2          # relative to the left top corner of the parent
COORD_LOCAL_CENTER = 4      # relative to the centre of the parent

# the edge formats
EDGE_NONE = 0
EDGE_CENTER = 1             # the ends are bound to the node centres
EDGE_BORDER = 2             # the ends are on the node borders

# the node types
TREE = 0
SIMPLE = 1
COMPOSITE = 2
REGION = 4
POINT = 8
COMMENT = 16                # excluded from the border bounds

# the layout roles
ROLE_NONE = 0
ROLE_INITIAL = 1
ROLE_FINAL = 2
ROLE_TERMINATE = 3
ROLE_ENTRY_POINT = 4
ROLE_EXIT_POINT = 5
ROLE_SHALLOW_HISTORY = 6
ROLE_DEEP_HISTORY = 7
ROLE_CHOICE = 8
ROLE_FORK = 9
ROLE_JOIN = 10
ROLE_SUBMACHINE = 11

# the flow directions and the layout modes
FLOW_DOWN = 0
FLOW_RIGHT = 1
LAYOUT_FIXED = 0
LAYOUT_ALTERNATE = 1
LAYOUT_ADAPTIVE = 2

# the result codes
OK = 0
BAD_PARAMETER = 1
NOT_FOUND = 2
TRANSFORM_ERROR = 3
INVALID = 4

COORD_EPS = 1e-6            # the coordinates below snap to zero
RECT_EPS = 1e-6             # the rect comparison tolerance
LENGTH_EPS = 1e-9           # the squared length of a degenerate segment
PADDING = 10.0
NODE_WIDTH = 300.0
NODE_HEIGHT = 200.0
SHELF_COLUMNS = 3
POINT_SIZE = 20.0
NODE_GAP = 40.0
LAYER_GAP = 60.0
LABEL_WIDTH = 80.0
LABEL_HEIGHT = 30.0
LAYOUT_SWEEPS = 8
LAYOUT_ASPECT = 1.6


class GeometryError(Exception):
    """A failed geometry operation with the library result code."""

    def __init__(self, code: int, message: str = '') -> None:
        super().__init__(message or 'geometry error %d' % code)
        self.code = code


def f32(value: float) -> float:
    """Return the value through a C float, as the float setters store it."""
    return struct.unpack('f', struct.pack('f', value))[0]


def round_half_away(value: float) -> float:
    """Return std::round(value): halves away from zero."""
    whole = float(math.trunc(value))
    if abs(value - whole) >= 0.5:
        whole += math.copysign(1.0, value)
    return whole


def round_number(value: float, signs: int) -> float:
    """Round to the decimal signs as the library does."""
    factor = 1.0
    for _ in range(signs):
        factor *= 10.0
    return round_half_away(value * factor) / factor


class Point:
    """A point; the absent point is None."""

    __slots__ = ('x', 'y')

    def __init__(self, x: float = 0.0, y: float = 0.0) -> None:
        self.x = x
        self.y = y

    def copy(self) -> 'Point':
        return Point(self.x, self.y)

    def __repr__(self) -> str:
        return '(x: %g, y: %g)' % (self.x, self.y)


class Rect:
    """A rect; the absent rect is None."""

    __slots__ = ('x', 'y', 'width', 'height')

    def __init__(self, x: float = 0.0, y: float = 0.0, width: float = 0.0,
                 height: float = 0.0) -> None:
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def copy(self) -> 'Rect':
        return Rect(self.x, self.y, self.width, self.height)

    def empty(self) -> bool:
        return self.x == 0.0 and self.y == 0.0 and self.width == 0.0 and \
            self.height == 0.0

    def __repr__(self) -> str:
        return '(x: %g, y: %g, w: %g, h: %g)' % (
            self.x, self.y, self.width, self.height)


def rect_center_point(rect: Rect, coord_format: int) -> Point:
    if coord_format == COORD_LOCAL_CENTER:
        return Point(rect.x, rect.y)
    return Point(rect.x + rect.width / 2.0, rect.y + rect.height / 2.0)


class Node:
    """A node of a tree: a state machine, a state, a region, a point."""

    def __init__(self, node_type: int, id_: str) -> None:
        self.type = node_type
        self.id = id_
        self.point: Optional[Point] = None
        self.rect: Optional[Rect] = None
        self.parent: Optional['Node'] = None
        self.children: List['Node'] = []
        self.role = ROLE_NONE
        self.min_rect: Optional[Rect] = None

    def add_child(self, child: 'Node') -> None:
        if not self.children and self.type == SIMPLE:
            self.type = COMPOSITE
        self.children.append(child)
        child.parent = self

    def __repr__(self) -> str:
        return 'Node(%s)' % self.id


class Edge:
    """An edge of a tree: a transition or a comment link."""

    def __init__(self, id_: str, source_id: str, target_id: str) -> None:
        self.id = id_
        self.source_id = source_id
        self.target_id = target_id
        self.source: Optional[Node] = None
        self.target: Optional[Node] = None
        self.polyline: Optional[List[Point]] = None
        self.source_point: Optional[Point] = None
        self.target_point: Optional[Point] = None
        self.label_point: Optional[Point] = None
        self.label_rect: Optional[Rect] = None

    def __repr__(self) -> str:
        return 'Edge(%s)' % self.id


class Tree:
    """The nodes and the edges of a state machine."""

    def __init__(self) -> None:
        self.nodes: List[Node] = []
        self.edges: List[Edge] = []


class Document:
    """The trees of a document with their coordinate formats."""

    def __init__(self, node_coord_format: int, edge_coord_format: int,
                 edge_pl_coord_format: int, edge_format: int) -> None:
        self.node_coord_format = node_coord_format
        self.edge_coord_format = edge_coord_format
        self.edge_pl_coord_format = edge_pl_coord_format
        self.edge_format = edge_format
        self.trees: List[Tree] = []
        self.bounding_rect: Optional[Rect] = None


class LayoutOptions:
    """The layered layout options; a value <= 0 selects the default."""

    def __init__(self) -> None:
        self.direction = FLOW_RIGHT
        self.mode = LAYOUT_ADAPTIVE
        self.aspect = LAYOUT_ASPECT
        self.node_gap = NODE_GAP
        self.layer_gap = LAYER_GAP
        self.padding = PADDING
        self.sweeps = LAYOUT_SWEEPS
        self.node_width = NODE_WIDTH
        self.node_height = NODE_HEIGHT
        self.point_size = POINT_SIZE
        self.label_width = LABEL_WIDTH
        self.label_height = LABEL_HEIGHT

    def copy(self) -> 'LayoutOptions':
        result = LayoutOptions()
        for name in vars(self):
            setattr(result, name, getattr(self, name))
        return result


def find_node_by_id(nodes: List[Node], id_: str) -> Optional[Node]:
    for node in nodes:
        if node.id == id_:
            return node
        if node.children:
            found = find_node_by_id(node.children, id_)
            if found is not None:
                return found
    return None


def node_has_geometry(nodes: List[Node]) -> bool:
    for node in nodes:
        if node.point is not None or node.rect is not None:
            return True
        if node.children and node_has_geometry(node.children):
            return True
    return False


def tree_has_geometry(tree: Tree) -> bool:
    if node_has_geometry(tree.nodes):
        return True
    return any(e.polyline is not None or e.source_point is not None or
               e.target_point is not None or e.label_point is not None or
               e.label_rect is not None for e in tree.edges)
