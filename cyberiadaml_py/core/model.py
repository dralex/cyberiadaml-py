# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The document model built from an L2-clean element tree
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
"""The document model built from an L2-clean element tree."""
from dataclasses import dataclass, field
from typing import Optional

from . import actions, meta

META_NAME = 'CGML_META'
COMPONENT_NAME = 'CGML_COMPONENT'

GEOMETRY_MODES = ('none', 'short', 'full')


@dataclass
class Point:
    """A point geometry."""

    x: float
    y: float


@dataclass
class Rect:
    """A rect geometry."""

    x: float
    y: float
    width: float
    height: float


@dataclass
class KeyDecl:
    """A key declaration of the document."""

    id: str
    for_kind: Optional[str]
    attr_name: Optional[str]
    attr_type: Optional[str]
    elem: object


@dataclass
class Extension:
    """A data item of a non-standard key, kept as read."""

    key: str
    text: Optional[str]
    elem: object


@dataclass
class Node:
    """The common part of the graph nodes."""

    id: Optional[str]
    elem: object
    name: Optional[str] = None
    formal_name: Optional[str] = None
    geometry: object = None
    color: Optional[str] = None
    parent: object = None
    line: Optional[int] = None
    extensions: list = field(default_factory=list)


@dataclass
class State(Node):
    """A simple or composite state."""

    blocks: list = field(default_factory=list)
    block_errors: list = field(default_factory=list)
    data: Optional[str] = None
    regions: list = field(default_factory=list)
    collapsed: bool = False


@dataclass
class Vertex(Node):
    """A pseudostate or a final state."""

    kind: Optional[str] = None


@dataclass
class Comment(Node):
    """A formal or informal comment."""

    kind: Optional[str] = None       # informal | formal
    body: Optional[str] = None
    markup: Optional[str] = None

    def component(self):
        """Return (id, type, params) of a component comment, or None."""
        name = (self.name or '').strip()
        if (self.kind or '').strip() != 'formal' or \
                not name.startswith(COMPONENT_NAME + ' '):
            return None
        params, _ = meta.parse(self.body)
        types = [p.value.strip() for p in params if p.name == 'type']
        return (name[len(COMPONENT_NAME) + 1:].strip(),
                types[0] if types else None,
                [p for p in params if p.name != 'type'])


@dataclass
class SubmachineState(Node):
    """A state with a nested state machine."""

    ref: Optional[str] = None
    regions: list = field(default_factory=list)


@dataclass
class Region:
    """A region of a composite state."""

    id: Optional[str]
    elem: object
    name: Optional[str] = None
    formal_name: Optional[str] = None
    geometry: object = None
    children: list = field(default_factory=list)
    parent: object = None
    line: Optional[int] = None
    extensions: list = field(default_factory=list)


@dataclass
class Transition:
    """A transition edge."""

    id: Optional[str]
    elem: object
    source: Optional[str] = None
    target: Optional[str] = None
    blocks: list = field(default_factory=list)
    block_errors: list = field(default_factory=list)
    data: Optional[str] = None
    polyline: list = field(default_factory=list)
    source_point: object = None
    target_point: object = None
    label_geometry: object = None
    color: Optional[str] = None
    parent: object = None
    line: Optional[int] = None
    extensions: list = field(default_factory=list)


@dataclass
class CommentLink:
    """A link edge of a comment to its subject."""

    id: Optional[str]
    elem: object
    source: Optional[str] = None
    target: Optional[str] = None
    pivot: Optional[str] = None
    chunk: Optional[str] = None
    polyline: list = field(default_factory=list)
    source_point: object = None
    target_point: object = None
    parent: object = None
    line: Optional[int] = None
    extensions: list = field(default_factory=list)


@dataclass
class StateMachine:
    """A top-level state machine graph."""

    id: Optional[str]
    elem: object
    name: Optional[str] = None
    formal_name: Optional[str] = None
    geometry: object = None
    marker: bool = False             # dStateMachine key present
    children: list = field(default_factory=list)
    transitions: list = field(default_factory=list)
    links: list = field(default_factory=list)
    # the parameters of a removed per-machine metadata node (dialect D-1)
    params: list = field(default_factory=list)
    line: Optional[int] = None
    extensions: list = field(default_factory=list)


@dataclass
class Document:
    """The document model."""

    root: object
    format: Optional[str] = None
    format_elem: object = None
    keys: list = field(default_factory=list)
    machines: list = field(default_factory=list)
    meta_comment: object = None
    meta_params: list = field(default_factory=list)
    meta_errors: list = field(default_factory=list)
    geometry_mode: str = 'none'
    # the reader's additions: the format label, the findings and the
    # top-level graphs the dialect pass took out (D-9)
    label: str = 'Cyberiada-GraphML-1.0'
    findings: list = field(default_factory=list)
    extension_graphs: list = field(default_factory=list)
    # an id the dialect pass gave (D-7f, D-7a) -> the id as written
    original_ids: dict = field(default_factory=dict)

    @property
    def meta_id(self):
        """Return the id of the metadata node, or None."""
        return self.meta_comment.id if self.meta_comment else None

    def param(self, name):
        """Return the value of a metadata parameter, or None."""
        for par in self.meta_params:
            if par.name == name:
                return par.value
        return None

    def transition_order(self):
        """Return the transitionOrder of the document."""
        return self.param('transitionOrder') or 'actionFirst'

    def event_propagation(self):
        """Return the eventPropagation of the document."""
        return self.param('eventPropagation') or 'block'

    def markup_language(self):
        """Return the markupLanguage of the document."""
        return self.param('markupLanguage') or 'plain'


def data_items(elem):
    """Return the ordered (key, data element) pairs of an element."""
    return [(d.get('key'), d) for d in elem if d.tag == 'data']


def iter_elements(root):
    """All (kind, element) pairs of the graphs, nodes and edges of the tree."""
    def walk_graph(graph):
        yield 'graph', graph
        for child in graph:
            if child.tag == 'node':
                yield from walk_node(child)
            elif child.tag == 'edge':
                yield 'edge', child

    def walk_node(node):
        yield 'node', node
        for child in node:
            if child.tag == 'graph':
                yield from walk_graph(child)

    for child in root:
        if child.tag == 'graph':
            yield from walk_graph(child)


def iter_machine_nodes(machine):
    """All node model objects of a state machine, region children included."""
    def walk(children):
        for child in children:
            yield child
            for region in getattr(child, 'regions', ()):
                yield from walk(region.children)
    yield from walk(machine.children)


def iter_nodes(document):
    """All node model objects of the document, region children included."""
    for machine in document.machines:
        yield from iter_machine_nodes(machine)


def iter_regions(document):
    """All region model objects of the document."""
    def walk(children):
        for child in children:
            for region in getattr(child, 'regions', ()):
                yield region
                yield from walk(region.children)
    for machine in document.machines:
        yield from walk(machine.children)


def data_value(elem, key):
    """Return the text of the first data tag with the key, or None."""
    for name, data in data_items(elem):
        if name == key:
            return data.text or ''
    return None


def _data_elem(elem, key):
    for name, data in data_items(elem):
        if name == key:
            return data
    return None


def _number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _geometry_object(child):
    if child.tag == 'rect':
        return Rect(_number(child.get('x')), _number(child.get('y')),
                    _number(child.get('width')), _number(child.get('height')))
    if child.tag == 'point':
        return Point(_number(child.get('x')), _number(child.get('y')))
    return None


def _geometry(elem, key='dGeometry'):
    data = _data_elem(elem, key)
    if data is None:
        return None
    for child in data:
        obj = _geometry_object(child)
        if obj is not None:
            return obj
    return None


def _points(elem, key):
    data = _data_elem(elem, key)
    if data is None:
        return []
    return [_geometry_object(c) for c in data if c.tag == 'point']


def _node_common(node):
    return {
        'id': node.get('id'),
        'elem': node,
        'name': data_value(node, 'dName'),
        'formal_name': data_value(node, 'dFormalName'),
        'geometry': _geometry(node),
        'color': data_value(node, 'dColor'),
    }


def _build_region(graph):
    region = Region(graph.get('id'), graph,
                    name=data_value(graph, 'dName'),
                    formal_name=data_value(graph, 'dFormalName'),
                    geometry=_geometry(graph))
    region.children = [_build_node(n) for n in graph if n.tag == 'node']
    return region


def _build_node(node):
    keys = [k for k, _ in data_items(node)]
    regions = [_build_region(g) for g in node if g.tag == 'graph']
    if 'dNote' in keys:
        return Comment(kind=data_value(node, 'dNote'),
                       body=data_value(node, 'dData'),
                       markup=data_value(node, 'dMarkup'),
                       **_node_common(node))
    if 'dVertex' in keys:
        return Vertex(kind=data_value(node, 'dVertex'), **_node_common(node))
    if 'dSubmachineState' in keys:
        return SubmachineState(ref=data_value(node, 'dSubmachineState'),
                               regions=regions, **_node_common(node))
    text = data_value(node, 'dData')
    blocks, errors = actions.parse(text)
    return State(blocks=blocks, block_errors=errors, data=text,
                 regions=regions,
                 collapsed=data_value(node, 'dCollapsed') is not None,
                 **_node_common(node))


def _build_edge(edge):
    items = data_items(edge)
    common = {
        'id': edge.get('id'),
        'elem': edge,
        'source': edge.get('source'),
        'target': edge.get('target'),
    }
    source_points = _points(edge, 'dSourcePoint')
    target_points = _points(edge, 'dTargetPoint')
    common['polyline'] = _points(edge, 'dGeometry')
    common['source_point'] = source_points[0] if source_points else None
    common['target_point'] = target_points[0] if target_points else None
    if items and items[0][0] == 'dPivot':
        return CommentLink(pivot=data_value(edge, 'dPivot'),
                           chunk=data_value(edge, 'dChunk'), **common)
    text = data_value(edge, 'dData')
    blocks, errors = actions.parse(text, transition=True)
    return Transition(blocks=blocks, block_errors=errors, data=text,
                      label_geometry=_geometry(edge, 'dLabelGeometry'),
                      color=data_value(edge, 'dColor'), **common)


def _build_machine(graph):
    machine = StateMachine(graph.get('id'), graph,
                           name=data_value(graph, 'dName'),
                           formal_name=data_value(graph, 'dFormalName'),
                           geometry=_geometry(graph),
                           marker=data_value(graph, 'dStateMachine')
                           is not None)
    for child in graph:
        if child.tag == 'node':
            machine.children.append(_build_node(child))
        elif child.tag == 'edge':
            built = _build_edge(child)
            if isinstance(built, CommentLink):
                machine.links.append(built)
            else:
                machine.transitions.append(built)
    return machine


def _find_meta(document):
    if not document.machines:
        return
    first = document.machines[0]
    for child in first.children:
        if isinstance(child, Comment) and child.kind == 'formal' \
                and child.name == META_NAME:
            document.meta_comment = child
            document.meta_params, document.meta_errors = \
                meta.parse(child.body)
            return


def build(parsed):
    """Build the document model from the parsed L2-clean tree."""
    root = parsed.root
    document = Document(root)
    for child in root:
        if child.tag == 'data' and child.get('key') == 'gFormat':
            if document.format_elem is None:
                document.format = child.text or ''
                document.format_elem = child
        elif child.tag == 'key':
            document.keys.append(KeyDecl(child.get('id'), child.get('for'),
                                         child.get('attr.name'),
                                         child.get('attr.type'), child))
        elif child.tag == 'graph':
            document.machines.append(_build_machine(child))
    _find_meta(document)
    mode = document.param('geometry')
    document.geometry_mode = mode if mode in GEOMETRY_MODES else 'none'
    return document
