# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The hierarchical tree geometry: conversions and the layout
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
"""The geometry of the hierarchical trees: a port of libhtreegeom.

The coordinate conversions between the formats, the bounding rects and the
layered layout (the full one and the update seeded by the drawing).
"""
from typing import List, Optional

from . import types
from .layout import check_options, layout_tree, place_trees
from .transform import (build_bounding_rect, convert_document_geometry,
                        convert_document_geometry_to_absolute,
                        convert_document_geometry_to_format)
from .types import (BAD_PARAMETER, COORD_ABSOLUTE, COORD_NONE, EDGE_BORDER,
                    Document, GeometryError, LayoutOptions, Rect,
                    tree_has_geometry)

__all__ = ['types', 'convert_document_geometry', 'build_bounding_rect',
           'reconstruct_document_geometry', 'update_document_geometry',
           'GeometryError', 'LayoutOptions']


def _prepare_update(doc: Document) -> None:
    """Convert to the canonical form keeping the preset label sizes."""
    presets = []
    for tree in doc.trees:
        for e in tree.edges:
            if e.label_rect is not None and e.source is not None and \
                    e.target is not None and \
                    (not (e.source.rect is not None or
                          e.source.point is not None) or
                     not (e.target.rect is not None or
                          e.target.point is not None)):
                presets.append((e, e.label_rect.copy()))
    convert_document_geometry_to_absolute(doc)
    for e, preset in presets:
        if e.label_rect is None:
            e.label_rect = Rect()
        e.label_rect.x = e.label_rect.y = 0.0
        e.label_rect.width = preset.width
        e.label_rect.height = preset.height


def _rebuild(doc: Document, reconstruct_sm: bool,
             layout: Optional[LayoutOptions], update: bool) -> None:
    if not doc.trees:
        raise GeometryError(BAD_PARAMETER, 'no trees')
    if layout is None:
        if not update:
            # the preserving fill-in of the decoding is not ported
            raise GeometryError(BAD_PARAMETER, 'no layout options')
        layout = LayoutOptions()
    opts = check_options(layout)
    node_fmt = doc.node_coord_format
    edge_fmt = doc.edge_coord_format
    pl_fmt = doc.edge_pl_coord_format
    edge_format = doc.edge_format
    many = len(doc.trees) > 1
    drawn: List[bool] = []
    if update:
        _prepare_update(doc)
        drawn = [tree_has_geometry(tree) for tree in doc.trees]
    for tree in doc.trees:
        # a document with several machines draws every border
        layout_tree(tree, reconstruct_sm or many, opts, update)
    if many:
        place_trees(doc.trees, opts, drawn if update else None)
    doc.node_coord_format = COORD_ABSOLUTE
    doc.edge_coord_format = COORD_ABSOLUTE
    doc.edge_pl_coord_format = COORD_ABSOLUTE
    doc.edge_format = EDGE_BORDER
    doc.bounding_rect = build_bounding_rect(doc)
    if node_fmt == COORD_NONE:
        # a geometry-less document reconstructs into the canonical form
        return
    convert_document_geometry_to_format(doc, node_fmt, edge_fmt, pl_fmt,
                                        edge_format)


def reconstruct_document_geometry(doc: Document, reconstruct_sm: bool,
                                  layout: LayoutOptions) -> None:
    """Lay the document out from its structure alone."""
    _rebuild(doc, reconstruct_sm, layout, False)


def update_document_geometry(doc: Document, reconstruct_sm: bool,
                             layout: Optional[LayoutOptions] = None) -> None:
    """Lay the geometry-less elements out, the drawing kept."""
    _rebuild(doc, reconstruct_sm, layout, True)
