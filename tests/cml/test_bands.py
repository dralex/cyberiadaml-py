# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
# The bands of a composite in the htgeom port
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
"""The bands of a composite beside the libhtreegeom test 67.

The header (the title, entry and internal actions) on top, the footer (the
exit) at the bottom, the content and its region between them.
"""
import pytest

from cyberiadaml_py import htgeom
from cyberiadaml_py.htgeom import types as ht

HEADER = 70.0
FOOTER = 40.0
EPS = 0.001


def _banded(with_region, footer=FOOTER):
    def node(parent, type_, id_):
        n = ht.Node(type_, id_)
        if parent is not None:
            parent.add_child(n)
        return n
    sm = node(None, ht.TREE, 'sm')
    comp = node(sm, ht.COMPOSITE, 'comp')
    comp.min_rect = ht.Rect(0.0, 0.0, 200.0, HEADER)
    comp.footer = footer
    holder = node(comp, ht.REGION, 'comp:') if with_region else comp
    a = node(holder, ht.SIMPLE, 'a')
    b = node(holder, ht.SIMPLE, 'b')
    doc = ht.Document(ht.COORD_ABSOLUTE, ht.COORD_ABSOLUTE, ht.COORD_ABSOLUTE,
                      ht.EDGE_BORDER)
    tree = ht.Tree()
    tree.nodes.append(sm)
    doc.trees.append(tree)
    e = ht.Edge('e-a-b', 'a', 'b')
    e.source, e.target = a, b
    tree.edges.append(e)
    return doc, comp, holder


def _bottom(holder):
    return max(c.rect.y + c.rect.height for c in holder.children)


@pytest.mark.parametrize('with_region', [False, True])
def test_bands(with_region):
    """The content between the bands, the update keeping the footer."""
    doc, comp, holder = _banded(with_region)
    opts = ht.LayoutOptions()
    htgeom.reconstruct_document_geometry(doc, True, opts)
    top = comp.rect.y + HEADER
    bottom = comp.rect.y + comp.rect.height - FOOTER
    assert all(c.rect.y > top for c in holder.children)
    inner = holder.rect if with_region else None
    assert abs(bottom - opts.padding - (
        inner.y + inner.height if inner else _bottom(holder))) < EPS
    htgeom.update_document_geometry(doc, True, opts)
    assert comp.rect.y + comp.rect.height - FOOTER - opts.padding >= \
        _bottom(holder) - EPS


def test_no_footer():
    """The footer adds its height; none is the layout of before."""
    heights = []
    for footer in (FOOTER, 0.0):
        doc, comp, _ = _banded(False, footer)
        htgeom.reconstruct_document_geometry(doc, True, ht.LayoutOptions())
        heights.append(comp.rect.height)
    assert abs(heights[0] - heights[1] - FOOTER) < EPS
