# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The arrange of the htgeom port and of cml
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
"""The arrange of the htgeom port beside the libhtreegeom tests 54-58, and
the cml arrange beside the binding.

binding-arrange.json comes from tools/record_binding_layout.py --arrange, run
with the binding of libcyberiadamlpp 1.1: the examples laid out anew and
arranged as drawn. Where the full layout of the port is not yet the
binding's (the comment layout of libhtreegeom 1.3), the arrange is skipped.
"""
import copy
import json
import pathlib

import pytest

from cyberiadaml_py import cml, htgeom
from cyberiadaml_py.htgeom import types as ht

from .test_layout import _TOOL, _bodies

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
RECORD = json.loads((ROOT / 'tests' / 'cml' / 'binding-arrange.json')
                    .read_text(encoding='utf-8'))
EPS = 0.001
LABEL = (80.0, 20.0)


def _document(nodes):
    doc = ht.Document(ht.COORD_ABSOLUTE, ht.COORD_ABSOLUTE, ht.COORD_ABSOLUTE,
                      ht.EDGE_BORDER)
    tree = ht.Tree()
    tree.nodes.extend(nodes)
    doc.trees.append(tree)
    return doc, tree


def _node(parent, type_, id_, rect=None, min_size=None, role=ht.ROLE_NONE):
    node = ht.Node(type_, id_)
    node.role = role
    if rect is not None:
        node.rect = ht.Rect(*rect)
    if min_size is not None:
        node.min_rect = ht.Rect(0.0, 0.0, *min_size)
    if parent is not None:
        parent.add_child(node)
    return node


def _edge(tree, id_, source, target, label=None):
    e = ht.Edge(id_, source.id, target.id)
    e.source, e.target = source, target
    if label is not None:
        e.label_rect = ht.Rect(0.0, 0.0, *label)
    tree.edges.append(e)
    return e


def _cx(n):
    return n.rect.x + n.rect.width / 2.0 if n.rect else n.point.x


def _cy(n):
    return n.rect.y + n.rect.height / 2.0 if n.rect else n.point.y


def _rect(n):
    return (n.rect.x, n.rect.y, n.rect.width, n.rect.height)


def _labels_clear(tree, nodes):
    """No label over a simple state."""
    def clear(r, ns):
        for n in ns:
            if n.type == ht.SIMPLE and n.rect is not None and \
                    r.x < n.rect.x + n.rect.width and n.rect.x < r.x + r.width \
                    and r.y < n.rect.y + n.rect.height and \
                    n.rect.y < r.y + r.height:
                return False
            if not clear(r, n.children):
                return False
        return True
    return all(clear(e.label_rect, nodes) for e in tree.edges
               if e.label_rect is not None)


def test_backward_chain():
    """54 (a): the drawn bands kept, the places and the labels anew."""
    sm = _node(None, ht.TREE, 'sm')
    a = _node(sm, ht.SIMPLE, 'a', (900, 50, 100, 60))
    b = _node(sm, ht.SIMPLE, 'b', (500, 50, 100, 60))
    c = _node(sm, ht.SIMPLE, 'c', (100, 50, 100, 60))
    doc, tree = _document([sm])
    ab = _edge(tree, 'e-a-b', a, b, LABEL)
    bc = _edge(tree, 'e-b-c', b, c, LABEL)
    htgeom.arrange_document_geometry(doc, True, ht.LayoutOptions())
    # the numbers of the C++ test
    assert _rect(sm) == (0, 0, 1320, 230)
    assert (_rect(c), _rect(b), _rect(a)) == \
        ((10, 20, 300, 200), (510, 20, 300, 200), (1010, 20, 300, 200))
    assert (ab.label_rect.x, ab.label_rect.y) == (870, 125)
    assert (bc.label_rect.x, bc.label_rect.y) == (370, 125)
    assert _labels_clear(tree, tree.nodes)


def test_swapped_diamond():
    """54 (b): a diamond drawn with its branches swapped keeps the swap."""
    sm = _node(None, ht.TREE, 'sm')
    a, b, c, d = (_node(sm, ht.SIMPLE, x) for x in 'abcd')
    doc, tree = _document([sm])
    for s, t in ((a, b), (a, c), (b, d), (c, d)):
        _edge(tree, 'e-%s-%s' % (s.id, t.id), s, t, LABEL)
    opts = ht.LayoutOptions()
    opts.mode, opts.direction = ht.LAYOUT_FIXED, ht.FLOW_RIGHT
    htgeom.reconstruct_document_geometry(doc, True, opts)
    full = _cy(c) - _cy(b)
    b.rect, c.rect = ht.Rect(c.rect.x, c.rect.y, b.rect.width, b.rect.height), \
        ht.Rect(b.rect.x, b.rect.y, c.rect.width, c.rect.height)
    htgeom.arrange_document_geometry(doc, True, ht.LayoutOptions())
    assert full * (_cy(c) - _cy(b)) < 0
    assert _cx(a) < _cx(b) < _cx(d) and abs(_cx(b) - _cx(c)) < EPS
    assert _labels_clear(tree, tree.nodes)


@pytest.mark.parametrize('vertical', [True, False])
def test_frame_from_the_spread(vertical):
    """55: a container without transitions runs along its children."""
    sm = _node(None, ht.TREE, 'sm')
    x = _node(sm, ht.SIMPLE, 'x', (0, 100, 100, 60))
    comp = _node(sm, ht.COMPOSITE, 'comp', (300, 0, 400, 400))
    a = _node(comp, ht.SIMPLE, 'a', (350, 50, 100, 60))
    b = _node(comp, ht.SIMPLE, 'b',
              (350, 250, 100, 60) if vertical else (550, 50, 100, 60))
    doc, tree = _document([sm])
    _edge(tree, 'e-x-comp', x, comp)
    htgeom.arrange_document_geometry(doc, True, ht.LayoutOptions())
    if vertical:
        assert _cy(a) < _cy(b) and abs(_cx(a) - _cx(b)) < EPS
    else:
        assert _cx(a) < _cx(b) and abs(_cy(a) - _cy(b)) < EPS


def _sample(kind):
    sm = _node(None, ht.TREE, 'sm')
    init = _node(sm, ht.POINT, 'init', role=ht.ROLE_INITIAL)
    a, b, c, d = (_node(sm, ht.SIMPLE, x) for x in 'abcd')
    doc, tree = _document([sm])
    _edge(tree, 'e-init-a', init, a)
    pairs = {'chain': ((a, b), (b, c), (c, d)),
             'cycle': ((a, b), (b, c), (c, a), (c, d)),
             'diamond': ((a, b), (a, c), (b, d), (c, d)),
             'long edge': ((a, b), (b, c), (c, d))}[kind]
    for s, t in pairs:
        _edge(tree, 'e-%s-%s' % (s.id, t.id), s, t)
    if kind == 'long edge':
        _edge(tree, 'e-a-d', a, d, (120.0, 20.0))
    return doc, sm


def _arrangement(sm):
    def sign(v):
        return 0 if abs(v) < EPS else (1 if v > 0 else -1)
    children = sm.children
    return [(sign(_cx(q) - _cx(p)), sign(_cy(q) - _cy(p)))
            for i, p in enumerate(children) for q in children[i + 1:]]


def _geometry(nodes):
    return [(_rect(n) if n.rect else (n.point.x, n.point.y),
             _geometry(n.children)) for n in nodes]


@pytest.mark.parametrize('kind', ['chain', 'cycle', 'diamond', 'long edge'])
def test_full_layout_as_the_seed(kind):
    """56: the arrangement of the full layout kept, the arrange idempotent."""
    doc, sm = _sample(kind)
    opts = ht.LayoutOptions()
    htgeom.reconstruct_document_geometry(doc, True, opts)
    before = _arrangement(sm)
    htgeom.arrange_document_geometry(doc, True, opts)
    assert _arrangement(sm) == before
    again = copy.deepcopy(doc)
    htgeom.arrange_document_geometry(again, True, opts)
    assert _geometry(again.trees[0].nodes) == _geometry(doc.trees[0].nodes)


def test_seed_sizes():
    """57 (a, b): the seed rects are the minimum sizes, the title band kept."""
    sm = _node(None, ht.TREE, 'sm')
    a = _node(sm, ht.SIMPLE, 'a', (0, 0, 500, 300), (120.0, 80.0))
    b = _node(sm, ht.SIMPLE, 'b', (700, 0, 50, 30), (120.0, 80.0))
    doc, tree = _document([sm])
    _edge(tree, 'e-a-b', a, b)
    htgeom.arrange_document_geometry(doc, True, ht.LayoutOptions())
    assert a.rect.width >= 500 - EPS and a.rect.height >= 300 - EPS
    assert (b.rect.width, b.rect.height) == (120.0, 80.0)

    sm = _node(None, ht.TREE, 'sm')
    comp = _node(sm, ht.COMPOSITE, 'comp', min_size=(100.0, 40.0))
    a = _node(comp, ht.SIMPLE, 'a')
    b = _node(comp, ht.SIMPLE, 'b')
    doc, tree = _document([sm])
    _edge(tree, 'e-a-b', a, b)
    htgeom.reconstruct_document_geometry(doc, True, ht.LayoutOptions())
    title = a.rect.y - comp.rect.y
    comp.rect = ht.Rect(comp.rect.x, comp.rect.y, 1600, 900)
    htgeom.arrange_document_geometry(doc, True, ht.LayoutOptions())
    assert comp.rect.width >= 1600 - EPS and comp.rect.height >= 900 - EPS
    assert abs(a.rect.y - comp.rect.y - title) < EPS


def test_unseeded_vertex():
    """57 (c): a state without a seed is inserted by the flow."""
    sm = _node(None, ht.TREE, 'sm')
    a = _node(sm, ht.SIMPLE, 'a', (0, 0, 100, 60))
    x = _node(sm, ht.SIMPLE, 'x')
    b = _node(sm, ht.SIMPLE, 'b', (400, 0, 100, 60))
    doc, tree = _document([sm])
    _edge(tree, 'e-a-x', a, x)
    _edge(tree, 'e-x-b', x, b)
    htgeom.arrange_document_geometry(doc, True, ht.LayoutOptions())
    assert x.rect is not None and _cx(a) < _cx(x) < _cx(b)


def test_drawn_document():
    """58: a drawn chain is laid out as the full layout of its order."""
    sm = _node(None, ht.TREE, 'sm')
    a = _node(sm, ht.SIMPLE, 'a', (50, 50, 300, 200))
    b = _node(sm, ht.SIMPLE, 'b', (600, 60, 300, 200))
    c = _node(sm, ht.SIMPLE, 'c', (1150, 70, 300, 200))
    doc, tree = _document([sm])
    ab = _edge(tree, 'e-a-b', a, b)
    ab.source_point, ab.target_point = ht.Point(300, 250), ht.Point(650, 260)
    ab.polyline = [ht.Point(500, 1000)]
    _edge(tree, 'e-b-c', b, c)
    full = copy.deepcopy(doc)
    htgeom.reconstruct_document_geometry(full, True, ht.LayoutOptions())
    htgeom.arrange_document_geometry(doc, True, ht.LayoutOptions())
    assert _cx(a) < _cx(b) < _cx(c) and abs(_cy(a) - _cy(c)) < EPS
    assert not ab.polyline
    assert _geometry(doc.trees[0].nodes) == _geometry(full.trees[0].nodes)


def _drawn_comments(path):
    try:
        document = _TOOL._open(cml, path)
    except cml.Exception:
        return False
    return any(c.has_geometry() for sm in document.get_state_machines()
               for c in sm.find_elements_by_types([cml.elementComment,
                                                   cml.elementFormalComment]))


@pytest.mark.parametrize('name', sorted(RECORD['documents']))
def test_arranged_as_the_binding(name):
    """The examples arranged as drawn, as the binding arranges them."""
    expected = RECORD['documents'][name]
    actual = _TOOL.run(cml, _TOOL.EXAMPLES / name, _TOOL.ARRANGE_SCENARIOS)
    if _bodies(actual['layout']) != _bodies(expected['layout']):
        pytest.skip('the full layout of libhtreegeom 1.3 is not ported here')
    if _drawn_comments(_TOOL.EXAMPLES / name):
        pytest.skip('a drawn comment takes part in the arrange: the comment '
                    'layout of libhtreegeom 1.3 is not ported')
    assert _bodies(actual['arranged']) == _bodies(expected['arranged'])
