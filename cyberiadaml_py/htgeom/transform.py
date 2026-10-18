# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The geometry transformations of the hierarchical trees
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
"""The coordinate conversions, the bounding rects and the edge attachments.

A port of htgeom.cpp of libhtreegeom: the same order of operations, so the
numbers come out the same.
"""
from typing import List, Optional, Tuple

from .segment import rect_corners, segment_rect_points
from .types import (BAD_PARAMETER, COMMENT, COORD_ABSOLUTE, COORD_EPS,
                    COORD_LEFT_TOP, COORD_LOCAL_CENTER, COORD_NONE,
                    EDGE_BORDER, EDGE_CENTER, INVALID, LENGTH_EPS, PADDING,
                    RECT_EPS, TREE, Document, Edge, GeometryError, Node,
                    Point, Rect, Tree, f32, rect_center_point)

Pts = List[Tuple[float, float]]
Rects = List[Tuple[Tuple[float, float], Tuple[float, float]]]


def node_is_comment(node: Optional[Node]) -> bool:
    return node is not None and node.type == COMMENT


def _rect_pts(rect: Rect):
    return rect_corners(rect.x, rect.y, rect.x + rect.width,
                        rect.y + rect.height)


def _resolved(node: Optional[Node]) -> bool:
    return node is not None and (node.rect is not None or
                                 node.point is not None)


def _nodes_collections(nodes: List[Node], points: Pts, rects: Rects,
                       skip_comments: bool) -> None:
    for node in nodes:
        if not (skip_comments and node_is_comment(node)):
            if node.point is not None:
                points.append((node.point.x, node.point.y))
            if node.rect is not None:
                rects.append(_rect_pts(node.rect))
        if node.children:
            _nodes_collections(node.children, points, rects, skip_comments)


def _edge_end(point: Optional[Point], node: Node) -> Optional[Point]:
    if point is not None:
        return point
    if node.rect is not None:
        return rect_center_point(node.rect, COORD_ABSOLUTE)
    return node.point


def _edges_collections(edges: List[Edge], points: Pts, rects: Rects,
                       skip_comments: bool) -> None:
    for edge in edges:
        if edge.source is None or edge.target is None:
            continue
        if skip_comments and (node_is_comment(edge.source) or
                              node_is_comment(edge.target)):
            continue
        if edge.polyline is not None:
            source = _edge_end(edge.source_point, edge.source)
            target = _edge_end(edge.target_point, edge.target)
            if source is not None and target is not None:
                points.append((source.x, source.y))
                points.extend((p.x, p.y) for p in edge.polyline)
                points.append((target.x, target.y))
        if edge.label_point is not None:
            points.append((edge.label_point.x, edge.label_point.y))
        if edge.label_rect is not None:
            rects.append(_rect_pts(edge.label_rect))


def has_border(tree: Tree) -> bool:
    """Tell whether the tree has the explicit state-machine border."""
    return len(tree.nodes) == 1 and tree.nodes[0].type == TREE and \
        tree.nodes[0].rect is not None


def _tree_collections(tree: Tree, points: Pts, rects: Rects) -> None:
    if has_border(tree):
        rects.append(_rect_pts(tree.nodes[0].rect))   # type: ignore
        return
    _nodes_collections(tree.nodes, points, rects, False)
    _edges_collections(tree.edges, points, rects, False)


def construct_bounding_rect(points: Pts, rects: Rects) -> Rect:
    """Fold the points and the rect corners into their bounds."""
    found = False
    min_x = min_y = max_x = max_y = 0.0
    for x, y in points + [c for r in rects for c in r]:
        if not found:
            min_x = max_x = x
            min_y = max_y = y
            found = True
        else:
            if x < min_x:
                min_x = x
            if x > max_x:
                max_x = x
            if y < min_y:
                min_y = y
            if y > max_y:
                max_y = y
    if not found:
        return Rect()
    return Rect(min_x, min_y, max_x - min_x, max_y - min_y)


def tree_bounding_rect(tree: Tree, skip_comments: bool) -> Rect:
    points: Pts = []
    rects: Rects = []
    _nodes_collections(tree.nodes, points, rects, skip_comments)
    _edges_collections(tree.edges, points, rects, skip_comments)
    return construct_bounding_rect(points, rects)


def build_bounding_rect(doc: Document) -> Rect:
    points: Pts = []
    rects: Rects = []
    for tree in doc.trees:
        _tree_collections(tree, points, rects)
    return construct_bounding_rect(points, rects)


def _content_rect(tree: Tree) -> Rect:
    """Return the content bounds of a bordered tree, no comments."""
    points: Pts = []
    rects: Rects = []
    _nodes_collections(tree.nodes[0].children, points, rects, True)
    _edges_collections(tree.edges, points, rects, True)
    return construct_bounding_rect(points, rects)


def check_geometry(doc: Document) -> int:
    copy = copy_document(doc)
    convert_document_geometry(copy, COORD_ABSOLUTE, COORD_ABSOLUTE,
                              COORD_ABSOLUTE, EDGE_BORDER)
    for tree in copy.trees:
        if not has_border(tree):
            continue
        content = _content_rect(tree)
        if not content.empty():
            b = tree.nodes[0].rect
            assert b is not None
            if content.x < b.x - RECT_EPS or content.y < b.y - RECT_EPS or \
                    content.x + content.width > b.x + b.width + RECT_EPS or \
                    content.y + content.height > \
                    b.y + b.height + RECT_EPS:
                return INVALID
    return 0


# the copies


def copy_node(src: Node) -> Node:
    dst = Node(src.type, src.id)
    dst.point = src.point.copy() if src.point is not None else None
    dst.rect = src.rect.copy() if src.rect is not None else None
    dst.role = src.role
    dst.min_rect = src.min_rect.copy() if src.min_rect is not None else None
    for child in src.children:
        copy = copy_node(child)
        copy.parent = dst
        dst.children.append(copy)
    return dst


def copy_edge(src: Edge) -> Edge:
    dst = Edge(src.id, src.source_id, src.target_id)
    if src.polyline is not None:
        dst.polyline = [p.copy() for p in src.polyline]
    for name in ('source_point', 'target_point', 'label_point',
                 'label_rect'):
        value = getattr(src, name)
        setattr(dst, name, value.copy() if value is not None else None)
    return dst


def copy_document(src: Document) -> Document:
    from .types import find_node_by_id
    dst = Document(src.node_coord_format, src.edge_coord_format,
                   src.edge_pl_coord_format, src.edge_format)
    for tree in src.trees:
        copy = Tree()
        copy.nodes = [copy_node(n) for n in tree.nodes]
        for edge in tree.edges:
            e = copy_edge(edge)
            e.source = find_node_by_id(copy.nodes, e.source_id)
            e.target = find_node_by_id(copy.nodes, e.target_id)
            copy.edges.append(e)
        dst.trees.append(copy)
    if src.bounding_rect is not None:
        dst.bounding_rect = src.bounding_rect.copy()
    return dst


# format to absolute


def _point_to_absolute(point: Point, parent, fmt: int) -> None:
    if fmt == COORD_NONE:
        raise GeometryError(BAD_PARAMETER, 'no coordinate format')
    if fmt == COORD_ABSOLUTE or parent is None:
        return
    if isinstance(parent, Point) or fmt == COORD_LEFT_TOP:
        point.x += parent.x
        point.y += parent.y
    else:
        point.x += parent.x + parent.width / 2.0
        point.y += parent.y + parent.height / 2.0


def _rect_to_absolute(rect: Rect, parent, fmt: int) -> None:
    if fmt == COORD_NONE:
        raise GeometryError(BAD_PARAMETER, 'no coordinate format')
    if fmt == COORD_ABSOLUTE or parent is None:
        return
    if fmt == COORD_LEFT_TOP:
        rect.x += parent.x
        rect.y += parent.y
    elif isinstance(parent, Point):
        rect.x += parent.x - rect.width / 2.0
        rect.y += parent.y - rect.height / 2.0
    else:
        rect.x += parent.x + parent.width / 2.0 - rect.width / 2.0
        rect.y += parent.y + parent.height / 2.0 - rect.height / 2.0


def _nodes_to_absolute(nodes: List[Node], parent: Rect, fmt: int) -> None:
    for node in nodes:
        if node.point is not None:
            _point_to_absolute(node.point, parent, fmt)
        if node.rect is not None:
            _rect_to_absolute(node.rect, parent, fmt)
        if node.children:
            _nodes_to_absolute(node.children, node.rect if node.rect
                               is not None else parent, fmt)


def _anchor(node: Node):
    return node.rect if node.rect is not None else node.point


def _edges_points_to_absolute(doc: Document) -> None:
    for tree in doc.trees:
        for edge in tree.edges:
            if _resolved(edge.source) and _resolved(edge.target):
                assert edge.source is not None and edge.target is not None
                if edge.source_point is not None:
                    _point_to_absolute(edge.source_point,
                                       _anchor(edge.source),
                                       doc.edge_coord_format)
                if edge.target_point is not None:
                    _point_to_absolute(edge.target_point,
                                       _anchor(edge.target),
                                       doc.edge_coord_format)
                for p in edge.polyline or []:
                    _point_to_absolute(p, _anchor(edge.source),
                                       doc.edge_pl_coord_format)
            else:
                # the geometry of an unresolved edge is dropped
                edge.source_point = edge.target_point = None
                edge.label_point = None
                edge.label_rect = None
                edge.polyline = None


def project_edge_to_borders(edge: Edge) -> None:
    """Fill the missing ends with the centres, project them on the borders."""
    source, target = edge.source, edge.target
    assert source is not None and target is not None
    if edge.source_point is None:
        edge.source_point = rect_center_point(source.rect, COORD_ABSOLUTE) \
            if source.rect is not None else source.point.copy()  # type: ignore
    if edge.target_point is None:
        edge.target_point = rect_center_point(target.rect, COORD_ABSOLUTE) \
            if target.rect is not None else target.point.copy()  # type: ignore
    sp, tp = edge.source_point, edge.target_point
    from_point, to_point = (sp.x, sp.y), (tp.x, tp.y)
    from .segment import _equal
    if not edge.polyline:
        from_toward, to_toward = to_point, from_point
        project_source = project_target = not _equal(from_point, to_point)
    else:
        first, last = edge.polyline[0], edge.polyline[-1]
        from_toward, to_toward = (first.x, first.y), (last.x, last.y)
        project_source = not _equal(from_point, from_toward)
        project_target = not _equal(to_toward, to_point)
    if project_source and source.rect is not None:
        r = source.rect
        crossings = segment_rect_points(from_point, from_toward, r.x, r.y,
                                        r.width, r.height)
        if crossings:
            sp.x, sp.y = crossings[0]
    if project_target and target.rect is not None:
        r = target.rect
        crossings = segment_rect_points(to_toward, to_point, r.x, r.y,
                                        r.width, r.height)
        if crossings:
            tp.x, tp.y = crossings[0]


def _edges_labels_to_absolute(doc: Document) -> None:
    yed = doc.node_coord_format == COORD_ABSOLUTE and \
        doc.edge_coord_format == COORD_LOCAL_CENTER and \
        doc.edge_pl_coord_format == COORD_ABSOLUTE and \
        doc.edge_format == EDGE_CENTER
    for tree in doc.trees:
        for edge in tree.edges:
            if not (_resolved(edge.source) and _resolved(edge.target)):
                continue
            assert edge.source is not None
            if edge.label_point is not None:
                parent = edge.source_point if yed else _anchor(edge.source)
                _point_to_absolute(edge.label_point, parent,
                                   doc.edge_coord_format)
            if edge.label_rect is not None:
                _rect_to_absolute(edge.label_rect, _anchor(edge.source),
                                  doc.edge_coord_format)


def convert_document_geometry_to_absolute(doc: Document) -> None:
    if not (doc.node_coord_format == COORD_ABSOLUTE and
            doc.edge_coord_format == COORD_ABSOLUTE and
            doc.edge_pl_coord_format == COORD_ABSOLUTE):
        # the top level of a tree is relative to the global origin
        origin = Rect()
        for tree in doc.trees:
            _nodes_to_absolute(tree.nodes, origin, doc.node_coord_format)
    if doc.edge_coord_format != COORD_ABSOLUTE or \
            doc.edge_pl_coord_format != COORD_ABSOLUTE:
        _edges_points_to_absolute(doc)
    # the labels are bound to the stored source points
    _edges_labels_to_absolute(doc)
    if doc.edge_format != EDGE_BORDER:
        for tree in doc.trees:
            for edge in tree.edges:
                if _resolved(edge.source) and _resolved(edge.target):
                    project_edge_to_borders(edge)
    doc.node_coord_format = COORD_ABSOLUTE
    doc.edge_coord_format = COORD_ABSOLUTE
    doc.edge_pl_coord_format = COORD_ABSOLUTE
    doc.edge_format = EDGE_BORDER


# absolute to format


def _snap(point: Point) -> None:
    if point.x != 0.0 and abs(point.x) < COORD_EPS:
        point.x = 0.0
    if point.y != 0.0 and abs(point.y) < COORD_EPS:
        point.y = 0.0


def _point_to_format(point: Point, parent, fmt: int) -> None:
    if fmt == COORD_NONE:
        raise GeometryError(BAD_PARAMETER, 'no coordinate format')
    if fmt == COORD_ABSOLUTE or parent is None:
        return
    if isinstance(parent, Point) or fmt == COORD_LEFT_TOP:
        point.x -= parent.x
        point.y -= parent.y
    else:
        point.x -= parent.x + parent.width / 2.0
        point.y -= parent.y + parent.height / 2.0
    _snap(point)


def _rect_to_format(rect: Rect, parent, fmt: int) -> None:
    if fmt == COORD_NONE:
        raise GeometryError(BAD_PARAMETER, 'no coordinate format')
    if fmt == COORD_ABSOLUTE or parent is None:
        return
    if fmt == COORD_LEFT_TOP:
        rect.x -= parent.x
        rect.y -= parent.y
    elif isinstance(parent, Point):
        rect.x -= parent.x - rect.width / 2.0
        rect.y -= parent.y - rect.height / 2.0
    else:
        rect.x -= parent.x + parent.width / 2.0 - rect.width / 2.0
        rect.y -= parent.y + parent.height / 2.0 - rect.height / 2.0


def _nodes_to_format(nodes: List[Node], parent: Rect, fmt: int) -> None:
    for node in nodes:
        if node.children:
            _nodes_to_format(node.children, node.rect if node.rect
                             is not None else parent, fmt)
        if node.point is not None:
            _point_to_format(node.point, parent, fmt)
        if node.rect is not None:
            _rect_to_format(node.rect, parent, fmt)


def _edges_points_to_format(doc: Document, fmt: int, pl_fmt: int) -> None:
    for tree in doc.trees:
        for edge in tree.edges:
            if not (_resolved(edge.source) and _resolved(edge.target)):
                continue
            assert edge.source is not None and edge.target is not None
            if edge.source_point is not None:
                _point_to_format(edge.source_point, _anchor(edge.source), fmt)
            if edge.target_point is not None:
                _point_to_format(edge.target_point, _anchor(edge.target), fmt)
            for p in edge.polyline or []:
                _point_to_format(p, _anchor(edge.source), pl_fmt)


def _project_center_point(point: Point, toward: Point, cx: float,
                          cy: float) -> None:
    dx = toward.x - point.x
    dy = toward.y - point.y
    len2 = dx * dx + dy * dy
    if len2 < LENGTH_EPS:
        return
    t = ((cx - point.x) * dx + (cy - point.y) * dy) / len2
    point.x += t * dx
    point.y += t * dy


def _center(node: Node) -> Tuple[float, float]:
    if node.rect is not None:
        return (node.rect.x + node.rect.width / 2.0,
                node.rect.y + node.rect.height / 2.0)
    assert node.point is not None
    return node.point.x, node.point.y


def _edges_to_center(doc: Document) -> None:
    for tree in doc.trees:
        for edge in tree.edges:
            if not (_resolved(edge.source) and _resolved(edge.target)):
                continue
            assert edge.source is not None and edge.target is not None
            scx, scy = _center(edge.source)
            tcx, tcy = _center(edge.target)
            sp, tp = edge.source_point, edge.target_point
            if sp is not None and tp is not None:
                old_source = sp.copy()
                if edge.polyline:
                    _project_center_point(sp, edge.polyline[0], scx, scy)
                    _project_center_point(tp, edge.polyline[-1], tcx, tcy)
                else:
                    _project_center_point(sp, tp, scx, scy)
                    _project_center_point(tp, old_source, tcx, tcy)


def _edges_labels_to_format(doc: Document, fmt: int, pl_fmt: int,
                            edge_fmt: int) -> None:
    yed = fmt == COORD_LOCAL_CENTER and pl_fmt == COORD_ABSOLUTE and \
        edge_fmt == EDGE_CENTER
    for tree in doc.trees:
        for edge in tree.edges:
            if not (_resolved(edge.source) and _resolved(edge.target)):
                continue
            assert edge.source is not None
            if edge.label_point is not None:
                parent = edge.source_point if yed else _anchor(edge.source)
                _point_to_format(edge.label_point, parent, fmt)
            if edge.label_rect is not None:
                _rect_to_format(edge.label_rect, _anchor(edge.source), fmt)


def convert_document_geometry_to_format(doc: Document, node_fmt: int,
                                        edge_fmt: int, pl_fmt: int,
                                        edge_format: int) -> None:
    if doc.bounding_rect is None:
        raise GeometryError(BAD_PARAMETER, 'no bounding rect')
    if not (doc.edge_coord_format == edge_fmt and
            doc.edge_pl_coord_format == pl_fmt and
            doc.edge_format == edge_format):
        if edge_format == EDGE_CENTER:
            _edges_to_center(doc)
        # the labels are bound to the projected source points
        _edges_labels_to_format(doc, edge_fmt, pl_fmt, edge_format)
        _edges_points_to_format(doc, edge_fmt, pl_fmt)
    if doc.node_coord_format != node_fmt:
        origin = Rect()
        for tree in doc.trees:
            _nodes_to_format(tree.nodes, origin, node_fmt)
    _rect_to_format(doc.bounding_rect, Rect(), node_fmt)
    doc.node_coord_format = node_fmt
    doc.edge_coord_format = edge_fmt
    doc.edge_pl_coord_format = pl_fmt
    doc.edge_format = edge_format


def convert_document_geometry(doc: Document, node_fmt: int, edge_fmt: int,
                              pl_fmt: int, edge_format: int) -> None:
    """Convert the document to the formats (the C library entry point)."""
    if not doc.trees:
        doc.node_coord_format = node_fmt
        doc.edge_coord_format = edge_fmt
        doc.edge_pl_coord_format = pl_fmt
        doc.edge_format = edge_format
        return
    convert_document_geometry_to_absolute(doc)
    doc.bounding_rect = build_bounding_rect(doc)
    convert_document_geometry_to_format(doc, node_fmt, edge_fmt, pl_fmt,
                                        edge_format)


# the helpers of the layout


def node_is_descendant(parent: Node, node: Node) -> bool:
    for child in parent.children:
        if child is node or node_is_descendant(child, node):
            return True
    return False


def children_bounding_rect(parent: Node, edges: List[Edge]) -> Rect:
    """Return the bounds of the children and the enclosed labels."""
    points: Pts = []
    rects: Rects = []
    _nodes_collections(parent.children, points, rects, True)
    for e in edges:
        if e.source is None or e.target is None or \
                node_is_comment(e.source) or node_is_comment(e.target) or \
                not node_is_descendant(parent, e.source) or \
                not node_is_descendant(parent, e.target):
            continue
        if e.label_point is not None:
            points.append((e.label_point.x, e.label_point.y))
        if e.label_rect is not None:
            rects.append(_rect_pts(e.label_rect))
    return construct_bounding_rect(points, rects)


def clean_tree_geometry(nodes: List[Node]) -> None:
    for node in nodes:
        node.rect = None
        node.point = None
        if node.children:
            clean_tree_geometry(node.children)


def shift_subtree(node: Node, dx: float, dy: float) -> None:
    if node.rect is not None:
        node.rect.x += dx
        node.rect.y += dy
    if node.point is not None:
        node.point.x += dx
        node.point.y += dy
    for child in node.children:
        shift_subtree(child, dx, dy)


def node_box(node: Node) -> Optional[Tuple[float, float, float, float]]:
    if node.rect is not None:
        return (node.rect.x, node.rect.y, node.rect.width, node.rect.height)
    if node.point is not None:
        return (node.point.x, node.point.y, 0.0, 0.0)
    return None


def _inset(margin: float, side: float) -> float:
    limit = side / 4.0
    if margin > PADDING:
        margin = PADDING
    return margin if margin < limit else limit


def attach_edge_minimal(edge: Edge) -> bool:
    """Attach the ends by the shortest way along no parallel border.

    False for the overlapping and nested nodes (the centre projection).
    """
    assert edge.source is not None and edge.target is not None
    a = node_box(edge.source)
    b = node_box(edge.target)
    if a is None or b is None:
        return False
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ax2, ay2 = ax + aw, ay + ah
    bx2, by2 = bx + bw, by + bh
    sepx = bx - ax2 if bx - ax2 > ax - bx2 else ax - bx2
    sepy = by - ay2 if by - ay2 > ay - by2 else ay - by2
    if sepx <= 0.0 and sepy <= 0.0:
        a_out = ax <= bx and ay <= by and ax2 >= bx2 and ay2 >= by2
        b_out = bx <= ax and by <= ay and bx2 >= ax2 and by2 >= ay2
        if not a_out and not b_out:
            return False
        if a_out:
            ox, oy, ox2, oy2 = ax, ay, ax2, ay2
            ix, iy, ix2, iy2 = bx, by, bx2, by2
        else:
            ox, oy, ox2, oy2 = bx, by, bx2, by2
            ix, iy, ix2, iy2 = ax, ay, ax2, ay2
        left, right, top, down = ix - ox, ox2 - ix2, iy - oy, oy2 - iy2
        if left <= right and left <= top and left <= down:
            c = (iy + iy2) / 2.0
            px, py, qx, qy = ox, c, ix, c
        elif right <= top and right <= down:
            c = (iy + iy2) / 2.0
            px, py, qx, qy = ox2, c, ix2, c
        elif top <= down:
            c = (ix + ix2) / 2.0
            px, py, qx, qy = c, oy, c, iy
        else:
            c = (ix + ix2) / 2.0
            px, py, qx, qy = c, oy2, c, iy2
        if not a_out:
            px, qx = qx, px
            py, qy = qy, py
    elif sepy <= 0.0:
        top = ay if ay > by else by
        bottom = ay2 if ay2 < by2 else by2
        py = qy = (top + bottom) / 2.0
        if bx >= ax2:
            px, qx = ax2, bx
        else:
            px, qx = ax, bx2
    elif sepx <= 0.0:
        left = ax if ax > bx else bx
        right = ax2 if ax2 < bx2 else bx2
        px = qx = (left + right) / 2.0
        if by >= ay2:
            py, qy = ay2, by
        else:
            py, qy = ay, by2
    elif sepx >= sepy:
        m = (sepx - sepy) / 2.0
        if bx >= ax2:
            px, qx = ax2, bx
        else:
            px, qx = ax, bx2
        if by >= ay2:
            py, qy = ay2 - _inset(m, ah), by + _inset(m, bh)
        else:
            py, qy = ay + _inset(m, ah), by2 - _inset(m, bh)
    else:
        m = (sepy - sepx) / 2.0
        if by >= ay2:
            py, qy = ay2, by
        else:
            py, qy = ay, by2
        if bx >= ax2:
            px, qx = ax2 - _inset(m, aw), bx + _inset(m, bw)
        else:
            px, qx = ax + _inset(m, aw), bx2 - _inset(m, bw)
    # the C library stores these through float
    edge.source_point = Point(f32(px), f32(py))
    edge.target_point = Point(f32(qx), f32(qy))
    return True


def reconstruct_edge_loop(edge: Edge, bottom_side: bool) -> None:
    """Draw a self-transition loop outside the right/bottom border."""
    assert edge.source is not None and edge.source.rect is not None
    r = edge.source.rect
    right = r.x + r.width
    bottom = r.y + r.height
    cx = r.x + r.width / 2.0
    cy = r.y + r.height / 2.0
    if bottom_side:
        edge.source_point = Point(cx - PADDING, bottom)
        edge.target_point = Point(cx + PADDING, bottom)
        edge.polyline = [Point(cx - PADDING, bottom + PADDING),
                         Point(cx + PADDING, bottom + PADDING)]
    else:
        edge.source_point = Point(right, cy - PADDING)
        edge.target_point = Point(right, cy + PADDING)
        edge.polyline = [Point(right + PADDING, cy - PADDING),
                         Point(right + PADDING, cy + PADDING)]


def grow_sm_border(tree: Tree) -> None:
    if not has_border(tree):
        return
    content = _content_rect(tree)
    if content.empty():
        return
    b = tree.nodes[0].rect
    assert b is not None
    x2 = b.x + b.width
    y2 = b.y + b.height
    cx2 = content.x + content.width + PADDING
    cy2 = content.y + content.height + PADDING
    if content.x - PADDING < b.x:
        b.x = content.x - PADDING
    if content.y - PADDING < b.y:
        b.y = content.y - PADDING
    b.width = (cx2 if cx2 > x2 else x2) - b.x
    b.height = (cy2 if cy2 > y2 else y2) - b.y
