# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The document model build tests
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
"""The document model build tests."""
from cyberiadaml_py.core import rules
from cyberiadaml_py.core.model import Comment, Point, Rect, State, Vertex

from .docbuilder import minimal


def build(data):
    """Return build."""
    ctx = rules.run_document(data, 'test.graphml')
    assert ctx.model is not None
    return ctx.model


def test_minimal_model():
    """Check minimal model."""
    doc = build(minimal())
    assert doc.format == 'Cyberiada-GraphML-1.0'
    assert len(doc.keys) == 8
    assert len(doc.machines) == 1
    machine = doc.machines[0]
    assert machine.id == 'G'
    assert machine.name == 'Test machine'
    assert machine.marker
    kinds = [type(c).__name__ for c in machine.children]
    assert kinds == ['Comment', 'Vertex', 'State']
    assert len(machine.transitions) == 1
    assert machine.transitions[0].source == 'init'
    assert machine.transitions[0].target == 'n0'


def test_meta_resolution():
    """Check meta resolution."""
    doc = build(minimal())
    assert doc.meta_comment is not None
    assert doc.param('standardVersion') == '1.0'
    assert doc.geometry_mode == 'none'
    assert doc.transition_order() == 'actionFirst'
    assert doc.event_propagation() == 'block'
    assert doc.markup_language() == 'plain'


def test_node_classification():
    """Check node classification."""
    doc = build(minimal())
    comment, vertex, state = doc.machines[0].children
    assert isinstance(comment, Comment)
    assert comment.kind == 'formal'
    assert comment.name == 'CGML_META'
    assert isinstance(vertex, Vertex)
    assert vertex.kind == 'initial'
    assert isinstance(state, State)
    assert state.name == 'Idle'
    assert state.regions == []


def test_geometry_and_actions():
    """Check geometry and actions."""
    doc = minimal() \
        .replace(b'      <data key="dName">Idle</data>',
                 b'      <data key="dName">Idle</data>\n'
                 b'      <data key="dData">entry/ on()</data>\n'
                 b'      <data key="dGeometry">'
                 b'<rect x="1.5" y="-2" width="30" height="40"/></data>') \
        .replace(b'      <data key="dVertex">initial</data>',
                 b'      <data key="dVertex">initial</data>\n'
                 b'      <data key="dGeometry"><point x="5" y="6"/></data>')
    machine = build(doc).machines[0]
    _, vertex, state = machine.children
    assert state.geometry == Rect(1.5, -2.0, 30.0, 40.0)
    assert vertex.geometry == Point(5.0, 6.0)
    assert [b.kind for b in state.blocks] == ['entry']
    assert state.blocks[0].behaviour == ['on()']


def test_comment_link_classification():
    """Check comment link classification."""
    doc = minimal().replace(
        b'<edge id="init-n0#1" source="init" target="n0"/>',
        b'<edge id="init-n0#1" source="init" target="n0"/>\n'
        b'    <edge id="c-n0#1" source="nMeta" target="n0">\n'
        b'      <data key="dPivot">dName</data>\n'
        b'      <data key="dChunk">Idle</data>\n'
        b'    </edge>')
    machine = build(doc).machines[0]
    assert len(machine.transitions) == 1
    assert len(machine.links) == 1
    link = machine.links[0]
    assert link.pivot == 'dName'
    assert link.chunk == 'Idle'
