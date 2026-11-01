# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
# The orthogonal routing of the htgeom port and of cml
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
"""The orthogonal routing of the port beside the libhtreegeom tests 62-65.

The cml routing beside the binding: binding-orthogonal.json comes from
tools/record_binding_layout.py --orthogonal, run with the binding of
libcyberiadamlpp 1.1: the examples laid
out anew and arranged with the orthogonal routes. Where the full layout of
the port is not yet the binding's, the routes are skipped.
"""
import json
import pathlib

import pytest

from cyberiadaml_py import cml, htgeom
from cyberiadaml_py.htgeom import types as ht

from .test_arrange import _drawn_comments
from .test_layout import _TOOL, _bodies

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
RECORD = json.loads((ROOT / 'tests' / 'cml' / 'binding-orthogonal.json')
                    .read_text(encoding='utf-8'))
EPS = 0.001
FRAMES = {'down': (ht.LAYOUT_FIXED, ht.FLOW_DOWN),
          'right': (ht.LAYOUT_FIXED, ht.FLOW_RIGHT),
          'adaptive': (ht.LAYOUT_ADAPTIVE, ht.FLOW_DOWN)}


def _options(frame):
    opts = ht.LayoutOptions()
    opts.routing = ht.ROUTING_ORTHOGONAL
    opts.mode, opts.direction = FRAMES[frame]
    return opts


def _node(parent, type_, id_, role=ht.ROLE_NONE):
    node = ht.Node(type_, id_)
    node.role = role
    if parent is not None:
        parent.add_child(node)
    return node


def _edge(tree, source, target, label=(60.0, 20.0)):
    e = ht.Edge('e-%s-%s' % (source.id, target.id), source.id, target.id)
    e.source, e.target = source, target
    if label is not None:
        e.label_rect = ht.Rect(0.0, 0.0, *label)
    tree.edges.append(e)
    return e


def _document(sm):
    doc = ht.Document(ht.COORD_ABSOLUTE, ht.COORD_ABSOLUTE, ht.COORD_ABSOLUTE,
                      ht.EDGE_BORDER)
    tree = ht.Tree()
    tree.nodes.append(sm)
    doc.trees.append(tree)
    return doc, tree


def _chain(e):
    return [e.source_point] + list(e.polyline or []) + [e.target_point]


def _oblique(tree):
    return sum(1 for e in tree.edges if e.source is not e.target
               for a, b in zip(_chain(e), _chain(e)[1:])
               if abs(a.x - b.x) > EPS and abs(a.y - b.y) > EPS)


def _side(p, r):
    """Return 1 inside, -1 outside, 0 on the border."""
    if p.x < r.x - EPS or p.x > r.x + r.width + EPS or \
            p.y < r.y - EPS or p.y > r.y + r.height + EPS:
        return -1
    if r.x + EPS < p.x < r.x + r.width - EPS and \
            r.y + EPS < p.y < r.y + r.height - EPS:
        return 1
    return 0


def _through(tree, nodes):
    """Count the bends of the routes inside the states."""
    return sum(1 for e in tree.edges for p in list(e.polyline or [])
               for n in nodes if n.rect is not None and not n.children and
               _side(p, n.rect) > 0)


@pytest.mark.parametrize('frame', sorted(FRAMES))
def test_fans(frame):
    """62: the ends of a state spread on its side, of a choice at one tip."""
    sm = _node(None, ht.TREE, 'sm')
    init = _node(sm, ht.POINT, 'init', ht.ROLE_INITIAL)
    s = _node(sm, ht.SIMPLE, 's')
    ch = _node(sm, ht.SIMPLE, 'ch', ht.ROLE_CHOICE)
    doc, tree = _document(sm)
    _edge(tree, init, s, None)
    for t in [_node(sm, ht.SIMPLE, id_) for id_ in 'ab'] + [ch]:
        _edge(tree, s, t)
    for id_ in 'dfg':
        _edge(tree, ch, _node(sm, ht.SIMPLE, id_))
    htgeom.reconstruct_document_geometry(doc, True, _options(frame))
    assert _oblique(tree) == 0
    ends = [e.source_point for e in tree.edges if e.source is s]
    assert all(_side(p, s.rect) == 0 for p in ends)
    assert len({(round(p.x, 3), round(p.y, 3)) for p in ends}) == len(ends)
    tips = {(round(e.source_point.x, 3), round(e.source_point.y, 3))
            for e in tree.edges if e.source is ch}
    assert len(tips) == 1
    assert _through(tree, sm.children) == 0


@pytest.mark.parametrize('frame', sorted(FRAMES))
def test_levels(frame):
    """64: the routes across the border of a composite, crossed once."""
    sm = _node(None, ht.TREE, 'sm')
    init = _node(sm, ht.POINT, 'init', ht.ROLE_INITIAL)
    s = _node(sm, ht.SIMPLE, 's')
    ch = _node(sm, ht.SIMPLE, 'ch', ht.ROLE_CHOICE)
    a = _node(sm, ht.SIMPLE, 'a')
    comp = _node(sm, ht.COMPOSITE, 'comp')
    x = _node(comp, ht.SIMPLE, 'x')
    y = _node(comp, ht.SIMPLE, 'y')
    doc, tree = _document(sm)
    _edge(tree, init, s, None)
    for source, target in ((s, ch), (ch, a), (ch, x), (x, y), (y, s),
                           (y, a)):
        _edge(tree, source, target)
    htgeom.reconstruct_document_geometry(doc, True, _options(frame))
    assert _oblique(tree) == 0
    for e in tree.edges:
        if (e.source in (x, y)) != (e.target in (x, y)):
            # inside or outside along the route, the border points aside
            sides = [s for s in (_side(p, comp.rect) for p in _chain(e)) if s]
            assert sum(1 for u, v in zip(sides, sides[1:]) if u != v) == 1
    assert _through(tree, sm.children + comp.children) == 0


def test_polylines_default():
    """65: the polylines the default; the routing of cml."""
    assert ht.LayoutOptions().routing == ht.ROUTING_POLYLINE
    assert cml.layoutRoutingPolyline != cml.layoutRoutingOrthogonal


@pytest.mark.parametrize('name', sorted(RECORD['documents']))
def test_routed_as_the_binding(name):
    """The examples with the orthogonal routes, as the binding routes them."""
    expected = RECORD['documents'][name]
    if 'crash' in expected:
        pytest.skip('the binding crashed on it')
    actual = _TOOL.run(cml, _TOOL.EXAMPLES / name, _TOOL.ORTHOGONAL_SCENARIOS)
    if _bodies(actual['layout']) != _bodies(expected['layout']):
        pytest.skip('the full layout of libhtreegeom 1.3 is not ported here')
    assert _bodies(actual['orthogonal']) == _bodies(expected['orthogonal'])
    if _drawn_comments(_TOOL.EXAMPLES / name):
        pytest.skip('a drawn comment takes part in the arrange: the comment '
                    'layout of libhtreegeom 1.3 is not ported')
    assert _bodies(actual['arranged']) == _bodies(expected['arranged'])
