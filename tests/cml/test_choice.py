# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The choices of the htgeom port
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
"""The choices of the htgeom port beside the libhtreegeom tests 59 and 60.

A small square, the transitions at the tips of its rhombus.
"""
import pytest

from cyberiadaml_py import htgeom
from cyberiadaml_py.htgeom import types as ht
from cyberiadaml_py.htgeom.transform import choice_tip

EPS = 0.001


def _fork():
    def node(parent, type_, id_, role=ht.ROLE_NONE):
        n = ht.Node(type_, id_)
        n.role = role
        if parent is not None:
            parent.add_child(n)
        return n
    sm = node(None, ht.TREE, 'sm')
    a = node(sm, ht.SIMPLE, 'a')
    c = node(sm, ht.SIMPLE, 'c', ht.ROLE_CHOICE)
    b = node(sm, ht.SIMPLE, 'b')
    d = node(sm, ht.SIMPLE, 'd')
    doc = ht.Document(ht.COORD_ABSOLUTE, ht.COORD_ABSOLUTE, ht.COORD_ABSOLUTE,
                      ht.EDGE_BORDER)
    tree = ht.Tree()
    tree.nodes.append(sm)
    doc.trees.append(tree)
    for s, t, label in ((a, c, None), (c, b, (60.0, 20.0)),
                        (c, d, (60.0, 20.0))):
        e = ht.Edge('e-%s-%s' % (s.id, t.id), s.id, t.id)
        e.source, e.target = s, t
        if label:
            e.label_rect = ht.Rect(0.0, 0.0, *label)
        tree.edges.append(e)
    return doc, tree, sm, a, c, b, d


def _at_tips(tree, c):
    r = c.rect
    tips = [(r.x, r.y + r.height / 2), (r.x + r.width, r.y + r.height / 2),
            (r.x + r.width / 2, r.y), (r.x + r.width / 2, r.y + r.height)]
    for e in tree.edges:
        p = e.source_point if e.source is c else \
            e.target_point if e.target is c else None
        if p is not None and not any(abs(p.x - x) < EPS and abs(p.y - y) < EPS
                                     for x, y in tips):
            return False
    return True


def test_square_choice():
    """59: the choice size, the larger side of a preset or a seed."""
    doc, _, _, a, c, b, d = _fork()
    htgeom.reconstruct_document_geometry(doc, True, ht.LayoutOptions())
    assert (c.rect.width, c.rect.height) == (ht.CHOICE_SIZE, ht.CHOICE_SIZE)
    doc, _, _, a, c, b, d = _fork()
    c.min_rect = ht.Rect(0.0, 0.0, 60.0, 20.0)
    htgeom.reconstruct_document_geometry(doc, True, ht.LayoutOptions())
    assert (c.rect.width, c.rect.height) == (60.0, 60.0)
    doc, _, _, a, c, b, d = _fork()
    for n, rect in ((a, (0, 0, 100, 60)), (c, (200, 0, 100, 50)),
                    (b, (400, 0, 100, 60)), (d, (400, 200, 100, 60))):
        n.rect = ht.Rect(*rect)
    htgeom.arrange_document_geometry(doc, True, ht.LayoutOptions())
    assert (c.rect.width, c.rect.height) == (100.0, 100.0)


@pytest.mark.parametrize('mode', ['full', 'arrange'])
def test_tips(mode):
    """60: the transitions of a choice end at its tips."""
    doc, tree, _, a, c, b, d = _fork()
    if mode == 'full':
        htgeom.reconstruct_document_geometry(doc, True, ht.LayoutOptions())
    else:
        for n, rect in ((a, (0, 100, 100, 60)), (c, (200, 110, 40, 40)),
                        (b, (400, 0, 100, 60)), (d, (400, 250, 100, 60))):
            n.rect = ht.Rect(*rect)
        htgeom.arrange_document_geometry(doc, True, ht.LayoutOptions())
    assert _at_tips(tree, c)


def test_tip_of_a_flat_choice():
    """The tip faces the point whatever the proportions of the rect."""
    c = ht.Node(ht.SIMPLE, 'c')
    c.role = ht.ROLE_CHOICE
    c.rect = ht.Rect(300, 320, 60, 20)
    assert (choice_tip(c, 500, 335).x, choice_tip(c, 500, 335).y) == (360, 330)
    assert (choice_tip(c, 330, 100).x, choice_tip(c, 330, 100).y) == (330, 320)
    state = ht.Node(ht.SIMPLE, 's')
    state.rect = c.rect
    assert choice_tip(state, 500, 335) is None
