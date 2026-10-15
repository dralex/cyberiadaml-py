"""Module implements building CyberiadaML schemes.

The 1.x interface over the standard-compliant core: the 1.x types become a
core model, the core writer writes it as a standard document. Function
graphs, outside the standard, follow the state machines.
"""
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple

from cyberiadaml_py import core
from cyberiadaml_py.core import writer
from cyberiadaml_py.core.keys import STANDARD_KEY_IDS
from cyberiadaml_py.types.cgml_scheme import CGML, CGMLDataNode, CGMLGraphml
from cyberiadaml_py.types.common import Point, Rectangle
from cyberiadaml_py.types.elements import (
    CGMLElements,
    CGMLFunction,
    CGMLStateMachine
)
from cyberiadaml_py.utils import to_list

COMPONENT_NAME = 'CGML_COMPONENT'
META_NAME = 'CGML_META'
META_ID = 'nMeta'
FUNCTION_NAME = 'CGML_FUNCTION'
INDENT = '  '
VERTEX_FIELDS = (
    ('initial_states', 'initial'),
    ('finals', 'final'),
    ('choices', 'choice'),
    ('terminates', 'terminate'),
    ('shallow_history', 'shallowHistory'),
    ('deep_history', 'deepHistory'),
    ('unknown_vertexes', None)
)


class CGMLBuilderException(Exception):
    """Logical errors during building CGML scheme."""

    ...


def create_empty_scheme() -> CGML:
    """Create empty CyberiadaML scheme."""
    return CGML(graphml=CGMLGraphml(
        [],
        'http://graphml.graphdrawing.org/xmlns',
    ))


def _geometry(value) -> Optional[core.Point | core.Rect]:
    if isinstance(value, Rectangle):
        return core.Rect(value.x, value.y, value.width, value.height)
    if isinstance(value, Point):
        return core.Point(value.x, value.y)
    return None


def _shape(node: CGMLDataNode) -> Optional[core.Point | core.Rect]:
    if node.rect is not None:
        return core.Rect(node.rect.x, node.rect.y, node.rect.width,
                         node.rect.height)
    points = to_list(node.point)
    return core.Point(points[0].x, points[0].y) if points else None


def _data_elem(node: CGMLDataNode) -> ET.Element:
    elem = ET.Element('data', {'key': node.key})
    if node.content is not None:
        elem.text = node.content
    if node.rect is not None:
        ET.SubElement(elem, 'rect', {
            'x': str(node.rect.x), 'y': str(node.rect.y),
            'width': str(node.rect.width), 'height': str(node.rect.height)})
    for point in to_list(node.point):
        ET.SubElement(elem, 'point', {'x': str(point.x), 'y': str(point.y)})
    return elem


def _apply(item, nodes: List[CGMLDataNode]) -> None:
    """Map unknown data onto the core fields; keep the rest as extensions."""
    for node in nodes:
        key = node.key
        if key == 'dFormalName' and hasattr(item, 'formal_name'):
            item.formal_name = node.content
        elif key == 'dCollapsed' and isinstance(item, core.State):
            item.collapsed = True
        elif key == 'dMarkup' and isinstance(item, core.Comment):
            item.markup = node.content
        elif key == 'dColor' and hasattr(item, 'color'):
            item.color = node.content
        elif key == 'dLabelGeometry' and isinstance(item, core.Transition):
            item.label_geometry = _shape(node)
        elif key == 'dSourcePoint' and hasattr(item, 'source_point'):
            item.source_point = _shape(node)
        elif key == 'dTargetPoint' and hasattr(item, 'target_point'):
            item.target_point = _shape(node)
        elif key == 'dChunk' and isinstance(item, core.CommentLink):
            item.chunk = node.content
        elif key not in STANDARD_KEY_IDS:
            item.extensions.append(
                core.Extension(key, node.content, _data_elem(node)))


def _parameters(params: List[Tuple[str, str]]) -> str:
    return '\n\n'.join('%s/ %s' % param for param in params)


class _MachineBuilder:
    """Build one core state machine from a 1.x state machine."""

    def __init__(self, sm_id: str, sm: CGMLStateMachine,
                 meta: Optional[core.Comment]) -> None:
        self.machine = core.StateMachine(sm_id, None, name=sm.name)
        if meta is not None:
            self.machine.children.append(meta)
        self.nodes: Dict[str, object] = {}
        self.order: List[Tuple[object, Optional[str]]] = []
        for node_id, component in sm.components.items():
            self.add(core.Comment(
                node_id, None, name='%s %s' % (COMPONENT_NAME, component.id),
                kind='formal', body=_parameters(
                    [('type', component.type)] +
                    list(component.parameters.items()))), None)
        for state_id, state in sm.states.items():
            self.state(state_id, state)
        for field, kind in VERTEX_FIELDS:
            for vertex_id, vertex in getattr(sm, field).items():
                self.add(core.Vertex(
                    vertex_id, None, name=vertex.data,
                    geometry=_geometry(vertex.position),
                    kind=kind or vertex.type), vertex.parent)
        for note_id, note in sm.notes.items():
            comment = core.Comment(
                note_id, None, name=note.name or None,
                geometry=_geometry(note.position),
                kind=note.type or 'informal', body=note.text)
            _apply(comment, note.unknown_datanodes)
            self.add(comment, note.parent)
        self.place()
        for transition in sm.transitions.values():
            self.edge(transition)

    def add(self, node, parent: Optional[str]) -> None:
        self.nodes[node.id] = node
        self.order.append((node, parent))

    def state(self, state_id: str, state) -> None:
        refs = [d.content for d in state.unknown_datanodes
                if d.key == 'dSubmachineState']
        node: core.State | core.SubmachineState
        if refs:
            node = core.SubmachineState(
                state_id, None, name=state.name or None,
                geometry=_geometry(state.bounds), color=state.color,
                ref=refs[0])
        else:
            node = core.State(
                state_id, None, name=state.name or None,
                geometry=_geometry(state.bounds), color=state.color,
                data=state.actions or None)
        _apply(node, [d for d in state.unknown_datanodes
                      if d.key != 'dSubmachineState'])
        self.add(node, state.parent)

    def place(self) -> None:
        for node, parent in self.order:
            if parent is None:
                self.machine.children.append(node)
                continue
            owner = self.nodes.get(parent)
            if not isinstance(owner, (core.State, core.SubmachineState)):
                raise CGMLBuilderException(
                    'The parent %r of %r is not a state.' %
                    (parent, getattr(node, 'id', None)))
            if not owner.regions:
                owner.regions.append(core.Region(None, None))
            owner.regions[0].children.append(node)

    def edge(self, transition) -> None:
        pivots = [d for d in transition.unknown_datanodes
                  if d.key == 'dPivot']
        if pivots:
            link = core.CommentLink(transition.id, None,
                                    source=transition.source,
                                    target=transition.target,
                                    pivot=pivots[0].content)
            _apply(link, [d for d in transition.unknown_datanodes
                          if d.key != 'dPivot'])
            self.machine.links.append(link)
            return
        label = transition.label_position
        edge = core.Transition(
            transition.id, None, source=transition.source,
            target=transition.target, data=transition.actions or None,
            polyline=[core.Point(p.x, p.y) for p in transition.position],
            label_geometry=core.Point(label.x, label.y) if label else None,
            color=transition.color)
        _apply(edge, transition.unknown_datanodes)
        self.machine.transitions.append(edge)


def _free(base: str, taken: set, template: str) -> str:
    name, number = base, 1
    while name in taken:
        number += 1
        name = template % (base, number)
    return name


def _nodes(items: list):
    for item in items:
        yield item
        for region in getattr(item, 'regions', []):
            yield from _nodes(region.children)


def _unique_ids(document: core.Document) -> None:
    """Make the per-machine 1.x ids unique in the document.

    A node id repeated in a later machine becomes <machine id>::<id> and a
    repeated edge id <id>#<N>, as the dialect repairs D-7f and D-7a read
    them.
    """
    nodes: set = set()
    edges: set = set()
    for machine in document.machines:
        renamed = {}
        for node in _nodes(machine.children):
            if node.id in nodes:
                new = _free('%s::%s' % (machine.id, node.id), nodes, '%s-%d')
                renamed[node.id] = new
                node.id = new
            nodes.add(node.id)
        for edge in list(machine.transitions) + list(machine.links):
            edge.source = renamed.get(edge.source, edge.source)
            edge.target = renamed.get(edge.target, edge.target)
            if edge.id in edges:
                edge.id = _free('%s#1' % edge.id, edges, '%s#%d')
            edges.add(edge.id)


def _document(elements: CGMLElements) -> core.Document:
    keys = [core.KeyDecl(k.id, k.for_, k.attr_name, k.attr_type, None)
            for group in elements.keys.values() for k in group]
    document = core.Document(None, format=core.FORMAT_STANDARD, keys=keys)
    machines = list(elements.state_machines.items())
    meta = None
    if machines:
        first = machines[0][1]
        values = dict(first.meta.values)
        if first.platform:
            values.setdefault('platform', first.platform)
        version = values.pop('standardVersion', None) or \
            first.standard_version or '1.0'
        params = [('standardVersion', version)] + list(values.items())
        document.meta_params = [core.Param(name, value, index)
                                for index, (name, value) in
                                enumerate(params)]
        meta = core.Comment(first.meta.id or META_ID, None, name=META_NAME,
                            kind='formal', body=_parameters(params))
        document.meta_comment = meta
    for index, (sm_id, sm) in enumerate(machines):
        document.machines.append(
            _MachineBuilder(sm_id, sm, meta if index == 0 else None).machine)
    _unique_ids(document)
    return document


def _function_graph(func: CGMLFunction) -> ET.Element:
    graph = ET.Element('graph', {'id': func.id, 'edgedefault': 'directed'})

    def data(owner: ET.Element, key: str,
             value: Optional[str] = None) -> None:
        elem = ET.SubElement(owner, 'data', {'key': key})
        if value is not None:
            elem.text = value

    data(graph, 'dFunction')
    data(graph, 'dName', FUNCTION_NAME)
    for key, value in func.parameters.items():
        if key not in ('dFunction', 'dName'):
            data(graph, key, value)
    vertexes: List[Tuple[str, object, Optional[str]]] = \
        [(i, v, v.data_type) for i, v in func.inputs.items()] + \
        [(i, v, v.data_type) for i, v in func.outputs.items()] + \
        [(i, v, v.block_type) for i, v in func.body.items()]
    for vertex_id, vertex, content in vertexes:
        node = ET.SubElement(graph, 'node', {'id': vertex_id})
        data(node, 'dVertex', getattr(vertex, 'type'))
        name = getattr(vertex, 'data')
        if name is not None:
            data(node, 'dName', name)
        if content is not None:
            data(node, 'dData', content)
        shape = _geometry(getattr(vertex, 'position'))
        if shape is not None:
            geometry = ET.SubElement(node, 'data', {'key': 'dGeometry'})
            attrs = {'x': str(shape.x), 'y': str(shape.y)}
            if isinstance(shape, core.Rect):
                attrs.update({'width': str(shape.width),
                              'height': str(shape.height)})
            ET.SubElement(geometry,
                          'rect' if isinstance(shape, core.Rect)
                          else 'point', attrs)
    for edge_id, transition in func.edges.items():
        edge = ET.SubElement(graph, 'edge', {
            'id': edge_id, 'source': transition.source,
            'target': transition.target})
        if transition.actions:
            data(edge, 'dData', transition.actions)
        else:
            for item in transition.unknown_datanodes:
                edge.append(_data_elem(item))
    return graph


def _append_functions(text: str, functions: List[CGMLFunction]) -> str:
    graphs = []
    for func in functions:
        graph = _function_graph(func)
        ET.indent(graph, space=INDENT, level=1)
        graphs.append(INDENT + ET.tostring(graph, encoding='unicode'))
    end = text.rindex('</graphml>')
    return text[:end] + '\n'.join(graphs) + '\n' + text[end:]


class CGMLBuilder:
    """Contains functions to build CGML scheme."""

    def __init__(self) -> None:
        """Initialize builder with an empty scheme."""
        self.scheme: CGML = create_empty_scheme()

    def build(self, elements: CGMLElements) -> str:
        """Build a standard CGML document from the elements."""
        if not elements.state_machines and not elements.functions:
            raise CGMLBuilderException('No state machines to build!')
        document = _document(elements)
        try:
            if document.machines:
                text = core.write(document)
            else:
                text = writer.render(document)
        except core.CGMLError as err:
            raise CGMLBuilderException(str(err)) from err
        if elements.functions:
            text = _append_functions(text, list(elements.functions.values()))
        return text
