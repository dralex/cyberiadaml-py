# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The element tree as the hierarchical trees of the geometry
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
"""The element tree as htgeom trees and the geometry written back.

What libcyberiadaml does with its document model: a state with children
becomes a composite node with one region node ('<id>:'), the CGML_META
comment takes no part unless it has geometry, the edges are the
transitions of a machine, then the comment subjects.
"""
from typing import Dict, List, Optional, Tuple, Union

from .. import htgeom
from ..htgeom import types as ht
from .elements import (Choice, Comment, CommentSubject, Element, State,
                       StateMachine, SubmachineState, Transition, Vertex)
from .enums import (TransitionType, actionTransition, elementCompositeState,
                    elementDeepHistory, elementEntryPoint, elementExitPoint,
                    elementFinal, elementFormalComment, elementInitial,
                    elementShallowHistory, elementTerminate,
                    geometryFormatCyberiada10, geometryFormatLegacyYED,
                    geometryFormatNone, geometryFormatQt, transitionLocal)
from .geometry import Point, Polyline, Rect

REGION_SUFFIX = ':'
META_NAME = 'CGML_META'
FORMATS = {
    int(geometryFormatNone): (ht.COORD_NONE, ht.COORD_NONE, ht.COORD_NONE,
                              ht.EDGE_NONE),
    int(geometryFormatLegacyYED): (ht.COORD_ABSOLUTE, ht.COORD_LOCAL_CENTER,
                                   ht.COORD_ABSOLUTE, ht.EDGE_CENTER),
    int(geometryFormatCyberiada10): (ht.COORD_LEFT_TOP, ht.COORD_LEFT_TOP,
                                     ht.COORD_LEFT_TOP, ht.EDGE_BORDER),
    int(geometryFormatQt): (ht.COORD_LOCAL_CENTER, ht.COORD_LOCAL_CENTER,
                            ht.COORD_LOCAL_CENTER, ht.EDGE_BORDER),
}
ROLES = {
    int(elementInitial): ht.ROLE_INITIAL,
    int(elementFinal): ht.ROLE_FINAL,
    int(elementTerminate): ht.ROLE_TERMINATE,
    int(elementEntryPoint): ht.ROLE_ENTRY_POINT,
    int(elementExitPoint): ht.ROLE_EXIT_POINT,
    int(elementShallowHistory): ht.ROLE_SHALLOW_HISTORY,
    int(elementDeepHistory): ht.ROLE_DEEP_HISTORY,
}
# the text block estimates: a 16 px monospace font
CHAR_WIDTH = 10.0
LINE_HEIGHT = 20.0
TEXT_MARGIN = 8.0
ACTION_HEAD = 6         # "entry/"
GUARD_EXTRA = 3         # " [" and "]"

EdgeOwner = Union[Transition, Tuple[Comment, int]]


def text_metrics(text: Optional[str]) -> Tuple[int, int]:
    """Return the longest line in characters and the number of lines."""
    if not text:
        return 0, 0
    lines = text.split('\n')
    count = len(lines) - (1 if text.endswith('\n') else 0)
    return max(len(line) for line in lines), count


def actions_metrics(actions, max_chars: int, lines: int) -> Tuple[int, int]:
    """Add the action lines as the writer formats them."""
    for action in actions:
        if action.get_type() == actionTransition:
            trigger = text_metrics(action.get_trigger())[0]
            guard = text_metrics(action.get_guard())[0]
            behavior = text_metrics(action.get_behavior())[0]
            if not trigger and not guard and not behavior:
                continue
            head = trigger + 1
            if guard:
                head += guard + GUARD_EXTRA
        else:
            head = ACTION_HEAD
        if head > max_chars:
            max_chars = head
        lines += 1
        chars, more = text_metrics(action.get_behavior())
        if chars > max_chars:
            max_chars = chars
        lines += more
    return max_chars, lines


def block_size(max_chars: int, lines: int) -> Tuple[float, float]:
    """Return the size of a text block."""
    return (max_chars * CHAR_WIDTH + 2 * TEXT_MARGIN,
            lines * LINE_HEIGHT + 2 * TEXT_MARGIN)


def _text_size(element: Element) -> Optional[Tuple[float, float]]:
    """Return the minimum size of a node from its texts."""
    opts = ht.LayoutOptions()
    if isinstance(element, Comment):
        max_chars, lines = text_metrics(element.get_body())
    elif isinstance(element, State):
        # a machine has none: cybNodeSM is 0 in the C library's type mask
        max_chars, lines = text_metrics(element._name)
        if lines == 0:
            lines = 1
        if isinstance(element, State) and \
                not isinstance(element, SubmachineState):
            max_chars, lines = actions_metrics(element._actions, max_chars,
                                               lines)
    else:
        return None
    w, h = block_size(max_chars, lines)
    composite = element.get_type() == elementCompositeState
    if isinstance(element, Comment) or (isinstance(element, State) and
                                        not composite):
        if w < opts.node_width:
            w = opts.node_width
        if h < opts.node_height:
            h = opts.node_height
    elif composite and w < opts.node_width:
        w = opts.node_width
    return w, h


def is_meta(element: Element) -> bool:
    """Tell the CGML_META comment."""
    return element.get_type() == elementFormalComment and \
        element._name == META_NAME


def _skipped(element: Element) -> bool:
    # the metainformation takes no part unless it has geometry
    return is_meta(element) and not element.has_geometry()


def _ht_rect(rect: Rect) -> Optional[ht.Rect]:
    return ht.Rect(rect.x, rect.y, rect.width, rect.height) \
        if rect.valid else None


def _ht_point(point: Point) -> Optional[ht.Point]:
    return ht.Point(point.x, point.y) if point.valid else None


def _ht_polyline(polyline: Polyline) -> Optional[List[ht.Point]]:
    points = [ht.Point(p.x, p.y) for p in polyline]
    return points or None


def to_rect(rect: Optional[ht.Rect]) -> Rect:
    """Return the interface rect of a tree rect."""
    return Rect(rect.x, rect.y, rect.width, rect.height) \
        if rect is not None else Rect()


def to_point(point: Optional[ht.Point]) -> Point:
    """Return the interface point of a tree point."""
    return Point(point.x, point.y) if point is not None else Point()


def to_polyline(points: Optional[List[ht.Point]]) -> Polyline:
    """Return the interface polyline of tree points."""
    return Polyline([Point(p.x, p.y) for p in points or []])


class Bridge:
    """The htgeom document of a document and its elements."""

    def __init__(self, doc, estimate: bool = False,
                 geometry_format=None) -> None:
        fmt = int(doc._geometry_format if geometry_format is None
                  else geometry_format)
        self.document = ht.Document(*FORMATS[fmt])
        self.estimate = estimate
        self.nodes: List[Tuple[Element, ht.Node]] = []
        self.regions: List[Tuple[State, ht.Node]] = []
        self.edges: List[Tuple[EdgeOwner, ht.Edge]] = []
        self.node_of: Dict[int, ht.Node] = {}
        self.region_of: Dict[int, ht.Node] = {}
        self.edge_of: Dict[object, ht.Edge] = {}
        for sm in doc.get_state_machines():
            self.document.trees.append(self._tree(sm))

    def _node(self, element: Element) -> Optional[ht.Node]:
        if _skipped(element):
            return None
        if isinstance(element, StateMachine):
            node_type = ht.TREE
        elif element.get_type() == elementCompositeState and \
                not isinstance(element, SubmachineState):
            node_type = ht.COMPOSITE
        elif isinstance(element, (State, Choice)):
            node_type = ht.SIMPLE
        elif isinstance(element, Comment):
            node_type = ht.COMMENT
        else:
            node_type = ht.POINT
        node = ht.Node(node_type, element.get_id())
        if isinstance(element, SubmachineState):
            node.role = ht.ROLE_SUBMACHINE
        elif isinstance(element, Choice):
            node.role = ht.ROLE_CHOICE
        else:
            node.role = ROLES.get(int(element.get_type()), ht.ROLE_NONE)
        if self.estimate:
            size = _text_size(element)
            if size is not None:
                node.min_rect = ht.Rect(0.0, 0.0, size[0], size[1])
        if isinstance(element, Vertex) and not isinstance(element, Choice):
            node.point = _ht_point(element._point)
        else:
            node.rect = _ht_rect(element._rect)    # type: ignore
        self.nodes.append((element, node))
        self.node_of[id(element)] = node
        children = [c for c in getattr(element, '_children', [])
                    if not isinstance(c, Transition)]
        parent = node
        if node_type == ht.COMPOSITE:
            assert isinstance(element, State)
            region = ht.Node(ht.REGION, element.get_id() + REGION_SUFFIX)
            region.rect = _ht_rect(element._region_rect)
            region.parent = node
            node.children.append(region)
            self.regions.append((element, region))
            self.region_of[id(element)] = region
            parent = region
        for child in children:
            child_node = self._node(child)
            if child_node is not None:
                child_node.parent = parent
                parent.children.append(child_node)
        return node

    def _tree(self, sm: StateMachine) -> ht.Tree:
        tree = ht.Tree()
        root = self._node(sm)
        assert root is not None
        tree.nodes.append(root)
        transitions = [t for t in sm.get_transitions()
                       if isinstance(t, Transition)]
        for t in transitions:
            edge = ht.Edge(t.get_id(), t.get_source_element_id(),
                           t.get_target_element_id())
            if self.estimate and t.has_action() and \
                    not t._label_rect.valid and not t._sp.valid and \
                    not t._tp.valid and not len(t._polyline) and \
                    not t._label_point.valid:
                # the label size preset from the action text
                max_chars, lines = actions_metrics([t._action], 0, 0)
                if lines > 0:
                    w, h = block_size(max_chars, lines)
                    edge.label_rect = ht.Rect(0.0, 0.0, w, h)
            edge.polyline = _ht_polyline(t._polyline)
            edge.source_point = _ht_point(t._sp)
            edge.target_point = _ht_point(t._tp)
            edge.label_point = _ht_point(t._label_point)
            if t._label_rect.valid:
                edge.label_rect = _ht_rect(t._label_rect)
            self.edges.append((t, edge))
            self.edge_of[id(t)] = edge
            tree.edges.append(edge)
        for comment in sm.get_comments():
            assert isinstance(comment, Comment)
            if _skipped(comment):
                continue
            for k, subject in enumerate(comment._subjects):
                element = subject.get_element()
                if _skipped(element):
                    continue
                target = element.get_target_element_id() \
                    if isinstance(element, Transition) else element.get_id()
                edge = ht.Edge(subject.get_id(), comment.get_id(), target)
                edge.source_point = _ht_point(subject._source)
                edge.target_point = _ht_point(subject._target)
                edge.polyline = _ht_polyline(subject._polyline)
                self.edges.append(((comment, k), edge))
                self.edge_of[(id(comment), k)] = edge
                tree.edges.append(edge)
        for edge in tree.edges:
            edge.source = ht.find_node_by_id(tree.nodes, edge.source_id)
            edge.target = ht.find_node_by_id(tree.nodes, edge.target_id)
            if edge.source is None or edge.target is None:
                raise ht.GeometryError(
                    ht.BAD_PARAMETER, 'Cannot find htree node by id '
                    '(%r, %r)' % (edge.source_id, edge.target_id))
        return tree

    def write_back(self, rebuilt: bool = True) -> None:
        """Copy the geometry of the trees to the elements.

        The C++ library rebuilds its elements after a geometry operation:
        the transitions come back local.
        """
        for element, node in self.nodes:
            if isinstance(element, Vertex) and \
                    not isinstance(element, Choice):
                element._point = to_point(node.point)
            else:
                element._rect = to_rect(node.rect)  # type: ignore
        for state, region in self.regions:
            state._region_rect = to_rect(region.rect)
        for owner, edge in self.edges:
            if isinstance(owner, Transition):
                if rebuilt:
                    owner._ttype = TransitionType(transitionLocal)
                owner._polyline = to_polyline(edge.polyline)
                owner._sp = to_point(edge.source_point)
                owner._tp = to_point(edge.target_point)
                owner._label_point = to_point(edge.label_point)
                owner._label_rect = to_rect(edge.label_rect)
            else:
                comment, k = owner
                subject: CommentSubject = comment._subjects[k]
                subject._source = to_point(edge.source_point)
                subject._target = to_point(edge.target_point)
                subject._polyline = to_polyline(edge.polyline)

    def bounding_rect(self) -> Rect:
        return to_rect(self.document.bounding_rect)


def convert(doc, geometry_format) -> Bridge:
    """Convert the geometry of the elements to the format (in place)."""
    bridge = Bridge(doc)
    htgeom.convert_document_geometry(bridge.document,
                                     *FORMATS[int(geometry_format)])
    bridge.write_back()
    return bridge
