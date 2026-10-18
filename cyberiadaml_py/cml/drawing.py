# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The geometry operations of the CyberiadaML interface
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
"""The geometry of the documents: formats, the import, the layout.

What the C++ library does around libcyberiadaml and libhtreegeom, over the
element tree: the bridge gives the trees, htgeom converts and lays out,
the geometry goes back to the elements.
"""
import math
from typing import List, Optional

from .. import htgeom
from ..htgeom import types as ht
from . import errors
from .bridge import FORMATS, Bridge
from .elements import Transition
from .enums import (geometryDeclarationFull, geometryFormatCyberiada10,
                    geometryFormatNone, geometryFormatQt)
from .geometry import Point, Rect

# the loose rects of the base format (7.2.2)
LOOSE_WIDTH = 300.0
LOOSE_HEIGHT = 200.0
LOOSE_PADDING = 10.0
LOOSE_MIN_SIZE = 20.0
# the decimal places of the rounded writing: positions finer than sizes
ROUND_SIGNS = 3
ROUND_POS_SIGNS = ROUND_SIGNS + 1


def _fail(error: Exception) -> errors.Exception:
    return errors.error(errors.ParametersException, str(error))


def _machines(doc) -> None:
    if not doc.get_state_machines():
        raise errors.error(errors.ParametersException,
                           'At least one state machine required')


def update_center(doc, bridge: Optional[Bridge]) -> None:
    """Set the centre point as the C++ library does after a rebuild."""
    r1 = bridge.bounding_rect() if bridge is not None else Rect()
    r2 = doc.get_bound_rect()
    if r1.almost_equal(r2):
        doc._center_point = Point(0.0, 0.0)
    elif doc._geometry_format == geometryFormatQt:
        doc._center_point = Point(r1.x, r1.y)
    else:
        doc._center_point = Point(0.0, 0.0)


# the loose rects: sized top down by the neighbours, bottom up by the content


def _children_extent(node: ht.Node):
    found = False
    w = h = 0.0
    for c in node.children:
        if c.rect is not None:
            cw = c.rect.x + c.rect.width
            ch = c.rect.y + c.rect.height
        elif c.point is not None:
            cw, ch = c.point.x, c.point.y
        elif c.children:
            # a container with no geometry shares the node coordinates
            extent = _children_extent(c)
            if extent is None:
                continue
            cw, ch = extent
        else:
            continue
        if not found or cw > w:
            w = cw
        if not found or ch > h:
            h = ch
        found = True
    return (w, h) if found else None


def _loose_bounds(node: ht.Node, siblings: List[ht.Node],
                  edges: List[ht.Edge], w: float, h: float):
    assert node.rect is not None
    x, y = node.rect.x, node.rect.y
    for s in siblings:
        if s is node or s.rect is None:
            continue
        dx = s.rect.x - x
        dy = s.rect.y - y
        if dx > 0.0 and dx >= abs(dy) and dx - LOOSE_PADDING < w:
            w = dx - LOOSE_PADDING
        if dy > 0.0 and dy > abs(dx) and dy - LOOSE_PADDING < h:
            h = dy - LOOSE_PADDING
    # the label is placed in the coordinates of the source node
    for e in edges:
        if e.source is not node:
            continue
        if e.label_point is not None:
            lx, ly = e.label_point.x, e.label_point.y
        elif e.label_rect is not None:
            lx, ly = e.label_rect.x, e.label_rect.y
        else:
            continue
        if lx <= 0.0 or ly <= 0.0:
            continue
        if lx >= ly:
            if lx - LOOSE_PADDING < w:
                w = lx - LOOSE_PADDING
        elif ly - LOOSE_PADDING < h:
            h = ly - LOOSE_PADDING
    return w, h


def _size_loose_node(node: ht.Node, avail_w: float, avail_h: float) -> None:
    r = node.rect
    assert r is not None
    extent = _children_extent(node)
    if r.width == 0.0:
        w = extent[0] + LOOSE_PADDING if extent is not None else LOOSE_WIDTH
        if w > avail_w:
            w = avail_w
        if w < LOOSE_MIN_SIZE:
            w = LOOSE_MIN_SIZE
        r.width = w
    if r.height == 0.0:
        h = extent[1] + LOOSE_PADDING if extent is not None \
            else LOOSE_HEIGHT
        if h > avail_h:
            h = avail_h
        if h < LOOSE_MIN_SIZE:
            h = LOOSE_MIN_SIZE
        r.height = h


def _size_loose_nodes(nodes: List[ht.Node], edges: List[ht.Edge],
                      avail_w: float, avail_h: float) -> None:
    for n in nodes:
        w, h = avail_w, avail_h
        if n.rect is not None:
            w -= n.rect.x
            h -= n.rect.y
            w, h = _loose_bounds(n, nodes, edges, w, h)
        if n.children:
            _size_loose_nodes(n.children, edges, w, h)
        if n.rect is not None:
            _size_loose_node(n, w, h)


# the operations


def import_geometry(doc, gf) -> None:
    """Bring the file geometry (left top, borders) to the format gf."""
    bridge = Bridge(doc, geometry_format=geometryFormatCyberiada10)
    if doc._meta.get_geometry() != geometryDeclarationFull:
        # the base format leaves the rect size to the consumer (7.2.2)
        for tree in bridge.document.trees:
            _size_loose_nodes(tree.nodes, tree.edges, math.inf, math.inf)
    try:
        htgeom.convert_document_geometry(bridge.document, *FORMATS[int(gf)])
    except ht.GeometryError as error:
        raise _fail(error) from None
    bridge.write_back()
    doc._geometry_format = gf
    update_center(doc, bridge)


def convert(doc, gf) -> None:
    """Convert the geometry of the document to the format gf."""
    if doc._geometry_format == gf:
        return
    _machines(doc)
    if gf == geometryFormatNone:
        # the C library converts no geometry to no coordinates
        raise errors.error(errors.ParametersException,
                           'Cannot convert the geometry to no format')
    bridge = Bridge(doc)
    try:
        htgeom.convert_document_geometry(bridge.document, *FORMATS[int(gf)])
    except ht.GeometryError as error:
        raise _fail(error) from None
    bridge.write_back()
    doc._geometry_format = gf
    update_center(doc, bridge)


def layout(doc, reconstruct_sm: bool, update: bool) -> None:
    """Lay the document out: anew, or the geometry-less elements only."""
    if doc._geometry_format == geometryFormatNone:
        doc._geometry_format = geometryFormatQt
    _machines(doc)
    if not update:
        # the layout rebuilds the geometry from the structure alone
        for sm in doc.get_state_machines():
            sm.clean_geometry()
    bridge = Bridge(doc, estimate=True)
    try:
        if update:
            htgeom.update_document_geometry(bridge.document, reconstruct_sm,
                                            htgeom.LayoutOptions())
        else:
            htgeom.reconstruct_document_geometry(bridge.document,
                                                 reconstruct_sm,
                                                 htgeom.LayoutOptions())
    except ht.GeometryError as error:
        raise _fail(error) from None
    bridge.write_back()
    update_center(doc, bridge)


def export(doc, round_: bool) -> Bridge:
    """Return the trees in the file format (left top, borders)."""
    bridge = Bridge(doc)
    try:
        htgeom.convert_document_geometry(
            bridge.document, *FORMATS[int(geometryFormatCyberiada10)])
    except ht.GeometryError as error:
        raise _fail(error) from None
    if round_:
        _round(bridge)
    return bridge


def _round_rect(r: Optional[ht.Rect]) -> None:
    if r is None:
        return
    x = ht.round_number(r.x, ROUND_POS_SIGNS)
    y = ht.round_number(r.y, ROUND_POS_SIGNS)
    r.width = ht.round_number(r.width, ROUND_SIGNS)
    r.height = ht.round_number(r.height, ROUND_SIGNS)
    r.x, r.y = x, y


def _round_point(p: Optional[ht.Point]) -> None:
    if p is not None:
        p.x = ht.round_number(p.x, ROUND_POS_SIGNS)
        p.y = ht.round_number(p.y, ROUND_POS_SIGNS)


def _round(bridge: Bridge) -> None:
    """Round as the C library does: the nodes with children, the edges."""
    for element, node in bridge.nodes:
        children = [c for c in getattr(element, '_children', [])
                    if not isinstance(c, Transition)]
        if children:
            _round_point(node.point)
            _round_rect(node.rect)
    for _, region in bridge.regions:
        _round_rect(region.rect)
    for _, edge in bridge.edges:
        _round_point(edge.source_point)
        _round_point(edge.target_point)
        _round_point(edge.label_point)
        for p in edge.polyline or []:
            _round_point(p)
