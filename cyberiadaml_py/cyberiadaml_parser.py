"""The module implements parsing CyberiadaML schemes.

The 1.x interface over the standard-compliant core: the core reads the
document in the permissive mode (standard or Lapki dialect), this module
fills the 1.x types from its model.
"""

import xml.etree.ElementTree as ET
from collections import defaultdict
from typing import DefaultDict, Dict, List, Optional, Tuple

from cyberiadaml_py import core
from cyberiadaml_py.types.cgml_scheme import (
    CGMLDataNode,
    CGMLEdge,
    CGMLGraph,
    CGMLKeyNode,
    CGMLNode,
    CGMLPointNode,
    CGMLRectNode
)
from cyberiadaml_py.types.common import Point, Rectangle
from cyberiadaml_py.types.elements import (
    CGMLBaseVertex,
    CGMLBlock,
    CGMLChoice,
    CGMLComponent,
    CGMLDeepHistory,
    CGMLElements,
    CGMLEntryPoint,
    CGMLExitPoint,
    CGMLFinal,
    CGMLFunction,
    CGMLInitialState,
    CGMLInput,
    CGMLLink,
    CGMLMeta,
    CGMLNote,
    CGMLOutput,
    CGMLRegion,
    CGMLShallowHistory,
    CGMLState,
    CGMLStateMachine,
    CGMLTerminate,
    CGMLTransition
)
from cyberiadaml_py.utils import to_list

VERTEX_TYPES = {
    'initial': ('initial_states', CGMLInitialState),
    'choice': ('choices', CGMLChoice),
    'final': ('finals', CGMLFinal),
    'terminate': ('terminates', CGMLTerminate),
    'shallowHistory': ('shallow_history', CGMLShallowHistory),
    'deepHistory': ('deep_history', CGMLDeepHistory),
    'entryPoint': ('entry_points', CGMLEntryPoint),
    'exitPoint': ('exit_points', CGMLExitPoint)
}

# the data keys the 1.x types hold in their own fields; any other data
# item of the element goes into unknown_datanodes
STATE_KEYS: Tuple[str, ...] = ('dName', 'dGeometry', 'dData', 'dColor',
                               'dSubmachineState', 'dCollapsed',
                               'dFormalName')
NOTE_KEYS: Tuple[str, ...] = ('dNote', 'dName', 'dGeometry', 'dData',
                              'dMarkup', 'dColor', 'dFormalName')
COMPONENT_KEYS: Tuple[str, ...] = ('dNote', 'dName', 'dData')
VERTEX_KEYS: Tuple[str, ...] = ('dVertex', 'dName', 'dGeometry', 'dColor',
                                'dFormalName')
TRANSITION_KEYS: Tuple[str, ...] = ('dData', 'dGeometry', 'dColor',
                                    'dLabelGeometry', 'dSourcePoint',
                                    'dTargetPoint')
LINK_KEYS: Tuple[str, ...] = ('dPivot', 'dChunk', 'dGeometry',
                              'dSourcePoint', 'dTargetPoint')
MACHINE_KEYS: Tuple[str, ...] = ('dStateMachine', 'dName', 'dGeometry',
                                 'dFormalName')
REGION_KEYS: Tuple[str, ...] = ('dRegion', 'dName', 'dGeometry',
                                'dFormalName')
META_KEYS: Tuple[str, ...] = ('dNote', 'dName', 'dData')


class CGMLParserException(Exception):
    """Logical errors during parsing CGML scheme."""

    ...


def create_empty_elements() -> CGMLElements:
    """Create CGMLElements with empty fields."""
    return CGMLElements(
        state_machines={},
        format='',
        keys=defaultdict(),
        functions={}
    )


def create_empty_state_machine() -> CGMLStateMachine:
    """Create CGMLStateMachine with empty fields."""
    return CGMLStateMachine(
        standard_version='',
        platform='',
        meta=CGMLMeta(
            id='',
            values={},
        ),
        states={},
        transitions={},
        finals={},
        choices={},
        terminates={},
        initial_states={},
        components={},
        notes={},
        shallow_history={},
        deep_history={},
        unknown_vertexes={}
    )


def _text(value: Optional[str]) -> str:
    # 1.x read the text through xmltodict, which strips it
    return (value or '').strip()


def _geometry(value) -> Optional[Point | Rectangle]:
    if isinstance(value, core.Rect):
        return Rectangle(x=value.x, y=value.y, width=value.width,
                         height=value.height)
    if isinstance(value, core.Point):
        return Point(x=value.x, y=value.y)
    return None


def _rect(value) -> Optional[Rectangle]:
    shape = _geometry(value)
    return shape if isinstance(shape, Rectangle) else None


def _point(value) -> Optional[Point]:
    shape = _geometry(value)
    return shape if isinstance(shape, Point) else None


def _data_node(elem: ET.Element) -> CGMLDataNode:
    rects = [CGMLRectNode(float(c.get('x', 0)), float(c.get('y', 0)),
                          float(c.get('width', 0)), float(c.get('height', 0)))
             for c in elem if c.tag == 'rect']
    points = [CGMLPointNode(float(c.get('x', 0)), float(c.get('y', 0)))
              for c in elem if c.tag == 'point']
    content = _text(elem.text) or None
    point: Optional[CGMLPointNode | List[CGMLPointNode]] = None
    if len(points) == 1:
        point = points[0]
    elif points:
        point = points
    return CGMLDataNode(elem.get('key') or '', content,
                        rects[0] if rects else None, point)


def _unknown(elem, known) -> List[CGMLDataNode]:
    if elem is None:
        return []
    return [_data_node(d) for d in elem
            if d.tag == 'data' and d.get('key') not in known]


def _graph(elem: ET.Element) -> CGMLGraph:
    """Turn a function graph element into the 1.x graph shape."""
    def datas(owner):
        return [_data_node(d) for d in owner if d.tag == 'data']

    nodes = [CGMLNode(n.get('id') or '', None, datas(n))
             for n in elem if n.tag == 'node']
    edges = [CGMLEdge(e.get('id') or '', e.get('source') or '',
                      e.get('target') or '', datas(e))
             for e in elem if e.tag == 'edge']
    return CGMLGraph(elem.get('id') or '', datas(elem),
                     elem.get('edgedefault'), nodes, edges)


def _values(document: core.Document,
            machine: core.StateMachine) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for param in document.meta_params:
        values.setdefault(param.name.strip(), _text(param.value))
    for param in machine.params:
        values[param.name.strip()] = _text(param.value)
    return values


class _MachineBuilder:
    """Fill one 1.x state machine from a core state machine."""

    def __init__(self, document: core.Document,
                 machine: core.StateMachine, first: bool) -> None:
        self.document = document
        self.sm = create_empty_state_machine()
        values = _values(document, machine)
        meta = getattr(document.meta_comment, 'elem', None)
        self.sm.meta = CGMLMeta(
            id=(document.meta_id or '') if first else '', values=values,
            unknown_datanodes=_unknown(meta, META_KEYS) if first else [])
        self.sm.platform = values.get('platform', '')
        self.sm.standard_version = values.get('standardVersion', '')
        self.sm.name = machine.name.strip() if machine.name else None
        self.sm.formal_name = machine.formal_name
        self.sm.bounds = _rect(machine.geometry)
        self.sm.unknown_datanodes = _unknown(machine.elem, MACHINE_KEYS)
        for child in machine.children:
            self.node(child, None, None)
        for transition in machine.transitions:
            self.transition(transition)
        for link in machine.links:
            self.link(link)

    def id(self, value: Optional[str]) -> str:
        # 1.x keeps the ids per machine, as written (no D-7f renames)
        return self.document.original_ids.get(value, value or '')

    def node(self, node, parent: Optional[str],
             region: Optional[str]) -> None:
        if isinstance(node, core.Comment):
            self.comment(node, parent, region)
        elif isinstance(node, core.Vertex):
            self.vertex(node, parent, region)
        else:
            submachine = node.ref if isinstance(
                node, core.SubmachineState) else None
            self.sm.states[self.id(node.id)] = CGMLState(
                name=_text(node.name),
                actions=_text(getattr(node, 'data', None)),
                unknown_datanodes=_unknown(node.elem, STATE_KEYS),
                parent=parent,
                bounds=_geometry(node.geometry),
                color=node.color,
                submachine=submachine,
                collapsed=getattr(node, 'collapsed', False),
                formal_name=node.formal_name,
                region=region,
                regions=[CGMLRegion(
                    id=r.id or '', name=r.name, formal_name=r.formal_name,
                    bounds=_rect(r.geometry),
                    unknown_datanodes=_unknown(r.elem, REGION_KEYS))
                    for r in node.regions]
            )
            for item in node.regions:
                for child in item.children:
                    self.node(child, self.id(node.id), item.id)

    def comment(self, node: core.Comment, parent: Optional[str],
                region: Optional[str]) -> None:
        if node is self.document.meta_comment:
            return
        component = node.component()
        if component is not None:
            ident, kind, params = component
            self.sm.components[self.id(node.id)] = CGMLComponent(
                id=ident, type=_text(kind),
                parameters={p.name.strip(): _text(p.value) for p in params},
                unknown_datanodes=_unknown(node.elem, COMPONENT_KEYS))
            return
        self.sm.notes[self.id(node.id)] = CGMLNote(
            name=_text(node.name),
            position=_geometry(node.geometry),
            text=_text(node.body),
            type=_text(node.kind) or 'informal',
            unknown_datanodes=_unknown(node.elem, NOTE_KEYS),
            parent=parent,
            formal_name=node.formal_name,
            markup=node.markup,
            color=node.color,
            region=region
        )

    def vertex(self, node: core.Vertex, parent: Optional[str],
               region: Optional[str]) -> None:
        kind = _text(node.kind)
        field, cls = VERTEX_TYPES.get(kind,
                                      ('unknown_vertexes', CGMLBaseVertex))
        getattr(self.sm, field)[self.id(node.id)] = cls(
            type=kind, data=node.name, position=_geometry(node.geometry),
            parent=parent, formal_name=node.formal_name, color=node.color,
            region=region,
            unknown_datanodes=_unknown(node.elem, VERTEX_KEYS))

    def edge_id(self, value: Optional[str], taken: dict) -> str:
        # an edge id renamed for a duplicate in another machine comes back
        ident = self.id(value)
        return (value or '') if ident in taken else ident

    def transition(self, edge: core.Transition) -> None:
        ident = self.edge_id(edge.id, self.sm.transitions)
        self.sm.transitions[ident] = CGMLTransition(
            id=ident,
            source=self.id(edge.source),
            target=self.id(edge.target),
            actions=_text(edge.data),
            unknown_datanodes=_unknown(edge.elem, TRANSITION_KEYS),
            color=edge.color,
            position=[Point(x=p.x, y=p.y) for p in edge.polyline],
            label_position=_geometry(edge.label_geometry),
            source_point=_point(edge.source_point),
            target_point=_point(edge.target_point)
        )

    def link(self, edge: core.CommentLink) -> None:
        ident = self.edge_id(edge.id, self.sm.links)
        self.sm.links[ident] = CGMLLink(
            id=ident,
            source=self.id(edge.source),
            target=self.id(edge.target),
            pivot=edge.pivot,
            chunk=edge.chunk,
            position=[Point(x=p.x, y=p.y) for p in edge.polyline],
            source_point=_point(edge.source_point),
            target_point=_point(edge.target_point),
            unknown_datanodes=_unknown(edge.elem, LINK_KEYS)
        )


def _keys(document: core.Document) -> DefaultDict[str, List[CGMLKeyNode]]:
    keys: DefaultDict[str, List[CGMLKeyNode]] = defaultdict(list)
    for decl in document.keys:
        keys[decl.for_kind or ''].append(
            CGMLKeyNode(decl.id, decl.for_kind or '', decl.attr_name,
                        decl.attr_type))
    return keys


class CGMLParser:
    """Class that contains functions for parsing CyberiadaML."""

    def __init__(self) -> None:
        """Сlass constructor."""
        self.elements: CGMLElements = create_empty_elements()

    def parse_func_from_graph(self, func_graph: CGMLGraph) -> CGMLFunction:
        """
        Parse a single graph into a CGMLFunction object.

        Args:
            func_graph: graph object representing a function.

        Returns:
            CGMLFunction instance with parsed data.
        """
        func_data: Dict[str, str] = {}
        data_list = to_list(func_graph.data)

        for data_item in data_list:
            if data_item.key != 'dName':
                func_data[data_item.key] = data_item.content or ''

        inputs: Dict[str, CGMLInput] = {}
        outputs: Dict[str, CGMLOutput] = {}
        blocks: Dict[str, CGMLBlock] = {}
        edges: Dict[str, CGMLTransition] = {}
        edge_list = to_list(func_graph.edge)
        for edge in edge_list:
            transition = CGMLTransition(
                id=edge.id,
                source=edge.source,
                target=edge.target,
                actions='',
                unknown_datanodes=to_list(edge.data) if edge.data else []
            )
            for data_node in transition.unknown_datanodes:
                if data_node.key == 'dData':
                    transition.actions = data_node.content or ''
                    break
            edges[edge.id] = transition

        nodes = to_list(func_graph.node)
        for node in nodes:
            node_data = to_list(node.data) if node.data else []

            # Node - data processing block
            node_type = None
            node_name = node.id
            node_data_type = None
            node_block = None
            node_position = None

            for data_item in node_data:
                if data_item.key == 'dVertex':
                    node_type = data_item.content
                elif data_item.key == 'dName':
                    node_name = data_item.content or node.id
                elif data_item.key == 'dData' and data_item.content:
                    if node_type == 'block':
                        node_block = data_item.content
                    else:
                        node_data_type = data_item.content
                elif data_item.key == 'dGeometry':
                    if data_item.rect is not None:
                        node_position = Rectangle(
                            x=data_item.rect.x,
                            y=data_item.rect.y,
                            width=data_item.rect.width,
                            height=data_item.rect.height
                        )

            if node_type == 'input':
                inputs[node.id] = CGMLInput(
                    type='input',
                    data=node_name,
                    position=node_position,
                    parent=None,
                    data_type=node_data_type
                )
            elif node_type == 'output':
                outputs[node.id] = CGMLOutput(
                    type='output',
                    data=node_name,
                    position=node_position,
                    parent=None,
                    data_type=node_data_type
                )
            elif node_type == 'block':
                blocks[node.id] = CGMLBlock(
                    type='block',
                    data=node_name,
                    position=node_position,
                    parent=None,
                    block_type=node_block
                )

        name = func_data.get('dName') or func_graph.id

        return CGMLFunction(
            id=func_graph.id,
            type='function',
            edges=edges,
            parameters=func_data,
            inputs=inputs,
            outputs=outputs,
            body=blocks,
            name=name
        )

    def parse_cgml(self, graphml: str) -> CGMLElements:
        """
        Parse CyberiadaGraphml scheme.

        Args:
            graphml (str): CyberiadaML scheme, standard or Lapki dialect.

        Returns:
            CGMLElements: state machines, keys, format and functions.
        Raises:
            CGMLParserException: the document cannot be read; the message
                names the first fatal finding of the core reader.
        """
        try:
            document = core.read(graphml)
        except core.CGMLError as err:
            raise CGMLParserException(str(err)) from err
        self.elements = CGMLElements(
            state_machines={
                machine.id: _MachineBuilder(document, machine,
                                            index == 0).sm
                for index, machine in enumerate(document.machines)},
            format=core.FORMAT_STANDARD,
            keys=_keys(document),
            functions={}
        )
        for graph in document.extension_graphs:
            function = self.parse_func_from_graph(_graph(graph))
            self.elements.functions[function.id] = function
        return self.elements
