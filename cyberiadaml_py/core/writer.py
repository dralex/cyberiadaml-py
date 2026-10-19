# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The writer of standard documents from the document model
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
"""The writer of standard documents from the document model."""
import copy
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Set, Tuple

from .dialect import FORMAT_VALUE
from .keys import STANDARD_BINDINGS, UNTYPED_KEYS
from .model import (META_NAME, Comment, CommentLink, Document, Point, Rect,
                    State, SubmachineState, Transition, Vertex)
from .tagtree import GRAPHML_NS

DECLARATION = '<?xml version="1.0" encoding="utf-8"?>\n'
INDENT = '  '
META_ID = 'nMeta'
REGION_SUFFIX = '::region'


def _number(value: float) -> str:
    text = repr(float(value))
    return text[:-2] if text.endswith('.0') else text


class _Writer:
    """One write: the output tree and the keys in use."""

    def __init__(self, document: Document) -> None:
        self.document = document
        self.used: List[Tuple[str, str]] = []
        self.declared: Dict[Tuple[str, str], object] = {
            (k.id, k.for_kind): k for k in document.keys}

    def data(self, parent: ET.Element, kind: str, key: str,
             text: Optional[str] = None) -> ET.Element:
        if (key, kind) not in self.used:
            self.used.append((key, kind))
        elem = ET.SubElement(parent, 'data', {'key': key})
        if text is not None:
            elem.text = text
        return elem

    def geometry(self, parent: ET.Element, kind: str, key: str,
                 geometry) -> None:
        if geometry is None:
            return
        data = self.data(parent, kind, key)
        shapes = geometry if isinstance(geometry, list) else [geometry]
        for shape in shapes:
            if isinstance(shape, Rect):
                ET.SubElement(data, 'rect', {
                    'x': _number(shape.x), 'y': _number(shape.y),
                    'width': _number(shape.width),
                    'height': _number(shape.height)})
            elif isinstance(shape, Point):
                ET.SubElement(data, 'point', {'x': _number(shape.x),
                                              'y': _number(shape.y)})

    def extensions(self, parent: ET.Element, kind: str, item) -> None:
        for ext in getattr(item, 'extensions', []):
            if ext.elem is not None:
                elem = copy.deepcopy(ext.elem)
                elem.tail = None
                parent.append(elem)
                # a key-less data is copied as it is, the re-read refuses it
                if ext.key is not None and (ext.key, kind) not in self.used:
                    self.used.append((ext.key, kind))
            elif ext.key is not None:
                self.data(parent, kind, ext.key, ext.text)

    def keys(self, root: ET.Element) -> None:
        # the document keeps its own declarations; one without any gets
        # those of appendix B for the keys in use
        written = set()
        for decl in self.document.keys:
            attrs = {'id': decl.id}
            for name, value in (('for', decl.for_kind),
                                ('attr.name', decl.attr_name),
                                ('attr.type', decl.attr_type)):
                if value is not None:
                    attrs[name] = value
            ET.SubElement(root, 'key', attrs)
            written.add(decl.id)
        if not self.document.keys:
            for key, kind in [k for k in STANDARD_BINDINGS
                              if k in self.used]:
                attrs = {'id': key, 'for': kind,
                         'attr.name': STANDARD_BINDINGS[(key, kind)]}
                if key not in UNTYPED_KEYS:
                    attrs['attr.type'] = 'string'
                ET.SubElement(root, 'key', attrs)
        for key, kind in self.used:
            if (key, kind) in STANDARD_BINDINGS or key in written:
                continue
            written.add(key)
            decl = self.declared.get((key, kind))
            name = getattr(decl, 'attr_name', None) or \
                (key[1].lower() + key[2:] if key.startswith('d') and
                 len(key) > 1 else key)
            ET.SubElement(root, 'key', {
                'id': key, 'for': kind, 'attr.name': name,
                'attr.type': getattr(decl, 'attr_type', None) or 'string'})

    def node(self, parent: ET.Element, node) -> None:
        elem = ET.SubElement(parent, 'node', {'id': node.id or ''})
        if isinstance(node, Comment):
            self.data(elem, 'node', 'dNote', node.kind or 'informal')
        elif isinstance(node, SubmachineState):
            self.data(elem, 'node', 'dSubmachineState', node.ref or '')
        elif isinstance(node, Vertex):
            self.data(elem, 'node', 'dVertex', node.kind)
        if node.name is not None:
            self.data(elem, 'node', 'dName', node.name)
        self.geometry(elem, 'node', 'dGeometry', node.geometry)
        if isinstance(node, Comment) and node.body is not None:
            text = node.body
            if node is self.document.meta_comment and \
                    self.document.meta_params:
                text = _parameters(self.document.meta_params)
            self.data(elem, 'node', 'dData', text)
        elif isinstance(node, State) and node.data is not None:
            self.data(elem, 'node', 'dData', node.data)
        if node.formal_name is not None:
            self.data(elem, 'node', 'dFormalName', node.formal_name)
        if isinstance(node, State) and node.collapsed:
            self.data(elem, 'node', 'dCollapsed')
        if node.color is not None:
            self.data(elem, 'node', 'dColor', node.color)
        if isinstance(node, Comment) and node.markup is not None:
            self.data(elem, 'node', 'dMarkup', node.markup)
        self.extensions(elem, 'node', node)
        if isinstance(node, SubmachineState):
            for region in node.regions:
                graph = ET.SubElement(elem, 'graph', {
                    'id': region.id or (node.id or '') + REGION_SUFFIX})
                for child in region.children:
                    self.node(graph, child)
        elif isinstance(node, State):
            taken: Set[str] = set()
            for region in node.regions:
                rid = region.id or _free((node.id or '') + REGION_SUFFIX,
                                         taken)
                taken.add(rid)
                graph = ET.SubElement(elem, 'graph', {'id': rid})
                self.data(graph, 'graph', 'dRegion')
                if region.name is not None:
                    self.data(graph, 'graph', 'dName', region.name)
                self.geometry(graph, 'graph', 'dGeometry', region.geometry)
                if region.formal_name is not None:
                    self.data(graph, 'graph', 'dFormalName',
                              region.formal_name)
                self.extensions(graph, 'graph', region)
                for child in region.children:
                    self.node(graph, child)

    def edge(self, parent: ET.Element, edge) -> None:
        elem = ET.SubElement(parent, 'edge', {
            'id': edge.id or '', 'source': edge.source or '',
            'target': edge.target or ''})
        if isinstance(edge, CommentLink):
            self.data(elem, 'edge', 'dPivot', edge.pivot or None)
            if edge.chunk is not None:
                self.data(elem, 'edge', 'dChunk', edge.chunk)
        elif isinstance(edge, Transition):
            if edge.data is not None:
                self.data(elem, 'edge', 'dData', edge.data)
            self.geometry(elem, 'edge', 'dLabelGeometry', edge.label_geometry)
        if edge.polyline:
            self.geometry(elem, 'edge', 'dGeometry', list(edge.polyline))
        self.geometry(elem, 'edge', 'dSourcePoint', edge.source_point)
        self.geometry(elem, 'edge', 'dTargetPoint', edge.target_point)
        if isinstance(edge, Transition) and edge.color is not None:
            self.data(elem, 'edge', 'dColor', edge.color)
        self.extensions(elem, 'edge', edge)

    def machine(self, root: ET.Element, machine, first: bool) -> None:
        graph = ET.SubElement(root, 'graph', {'id': machine.id or '',
                                              'edgedefault': 'directed'})
        self.data(graph, 'graph', 'dStateMachine')
        if machine.name is not None:
            self.data(graph, 'graph', 'dName', machine.name)
        self.geometry(graph, 'graph', 'dGeometry', machine.geometry)
        if machine.formal_name is not None:
            self.data(graph, 'graph', 'dFormalName', machine.formal_name)
        self.extensions(graph, 'graph', machine)
        meta = self.document.meta_comment
        children = list(machine.children)
        if first:
            if meta is not None and meta in children:
                children.remove(meta)
                children.insert(0, meta)
            elif meta is None and self.document.meta_params:
                children.insert(0, self.meta_node())
        for child in children:
            self.node(graph, child)
        for edge in list(machine.transitions) + list(machine.links):
            self.edge(graph, edge)

    def meta_node(self) -> Comment:
        taken = {n.id for m in self.document.machines for n in m.children}
        return Comment(_free(META_ID, taken), None, name=META_NAME,
                       kind='formal',
                       body=_parameters(self.document.meta_params))

    def write(self) -> str:
        root = ET.Element('graphml', {'xmlns': GRAPHML_NS})
        gformat = ET.SubElement(root, 'data', {'key': 'gFormat'})
        gformat.text = FORMAT_VALUE
        self.used.append(('gFormat', 'graphml'))
        graphs = ET.Element('graphs')
        for index, machine in enumerate(self.document.machines):
            self.machine(graphs, machine, index == 0)
        self.keys(root)
        root.extend(list(graphs))
        indent(root)
        return DECLARATION + ET.tostring(root, encoding='unicode') + '\n'


def indent(element: ET.Element, space: str = INDENT, level: int = 0) -> None:
    """Indent an element tree in place as ElementTree.indent does (3.9+)."""
    if len(element):
        _indent(element, space, level)


def _indent(element: ET.Element, space: str, level: int) -> None:
    inner = '\n' + space * (level + 1)
    if not element.text or not element.text.strip():
        element.text = inner
    child = element[0]
    for child in element:
        if len(child):
            _indent(child, space, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = inner
    # the last child closes the parent at its level
    if not (child.tail or '').strip():
        child.tail = '\n' + space * level


def _parameters(params) -> str:
    return '\n\n'.join('%s/ %s' % (p.name, p.value) for p in params)


def _free(base: str, taken: set) -> str:
    name, number = base, 2
    while name in taken:
        name = '%s-%d' % (base, number)
        number += 1
    return name


def render(document: Document) -> str:
    """Return the document text without the check of write()."""
    return _Writer(document).write()


def write(document: Document) -> str:
    """Write a standard document; raise CGMLError on a MUST violation."""
    from .reader import read
    text = render(document)
    read(text, strict=True)
    return text
