"""Module contains the types of parsed scheme's elements."""
from typing import (
    List,
    Dict,
    DefaultDict,
    Literal,
    Optional,
    Union
)

from pydantic import BaseModel, Field
from pydantic.dataclasses import dataclass

try:
    from .cgml_scheme import CGMLDataNode, CGMLKeyNode
    from .common import Point, Rectangle
except ImportError:
    from cyberiadaml_py.types.cgml_scheme import CGMLDataNode, CGMLKeyNode
    from cyberiadaml_py.types.common import Point, Rectangle

AvailableKeys = DefaultDict[str, List[CGMLKeyNode]]

CGMLVertexType = Literal['choice', 'initial',
                         'final', 'terminate', 'shallowHistory', 'deepHistory']
CGMLNoteType = Literal['formal', 'informal']


@dataclass
class CGMLBaseVertex:
    """
    The type represents pseudo-nodes.

    type: content from nested <data>-node with key 'dVertex'.
    data: content from nested <data>-node with key 'dName'.
    position: content from nested <data>-node with key 'dGeometry'.
    parent: parent node id.
    """

    type: str
    data: Optional[str] = None
    position: Optional[Union[Point, Rectangle]] = None
    parent: Optional[str] = None
    formal_name: Optional[str] = None
    color: Optional[str] = None
    region: Optional[str] = None
    unknown_datanodes: List[CGMLDataNode] = Field(default_factory=list)


@dataclass
class CGMLInput(CGMLBaseVertex):
    """The vertex representing the input parameter of the function."""

    data_type: Optional[str] = None


@dataclass
class CGMLOutput(CGMLBaseVertex):
    """The vertex representing the output parameter of the function."""

    data_type: Optional[str] = None


@dataclass
class CGMLBlock(CGMLBaseVertex):
    """A vertex representing a block of code or an action inside a function."""

    block_type: Optional[str] = None


@dataclass
class CGMLState:
    """
    Data class with information about state.

    State is <node>, that not connected with meta node,
    doesn't have data node with key 'dNote'

    Parameters:
    name: content of data node with key 'dName'.
    actions: content of data node with key 'dData'.
    bounds: x, y, width, height properties of data node with key 'dGeometry'.
    parent: parent state id.
    color: content of data node with key 'dColor'.
    unknownDatanodes: all datanodes, whose information is not included.
    """

    name: str
    actions: str
    unknown_datanodes: List[CGMLDataNode]
    parent: Optional[str] = None
    bounds: Optional[Union[Rectangle, Point]] = None
    color: Optional[str] = None
    submachine: Optional[str] = None
    collapsed: bool = False
    formal_name: Optional[str] = None
    region: Optional[str] = None
    regions: List['CGMLRegion'] = Field(default_factory=list)


@dataclass
class CGMLRegion:
    """
    A region of a state: its child graph.

    id: the graph id; name, formal_name: dName, dFormalName;
    bounds: dGeometry; unknown_datanodes: the extension data.
    """

    id: str
    name: Optional[str] = None
    formal_name: Optional[str] = None
    bounds: Optional[Rectangle] = None
    unknown_datanodes: List[CGMLDataNode] = Field(default_factory=list)


@dataclass
class CGMLComponent:
    """
    Data class with information about component.

    Component is formal note, that includes <data>-node with key 'dName'
    and content 'CGML_COMPONENT'.
    parameters: content of data node with key 'dData'.
    """

    id: str
    type: str
    parameters: Dict[str, str]
    unknown_datanodes: List[CGMLDataNode] = Field(default_factory=list)


@dataclass
class CGMLInitialState(CGMLBaseVertex):
    """
    Data class with information about initial state (pseudo node).

    Intiial state is <node>, that contains data node with key 'dVertex'
    and content 'initial'.
    """

    ...


@dataclass
class CGMLShallowHistory(CGMLBaseVertex):
    """
    Data class with information about shallow history node (pseudo node).

    ShallowHistory is <node>, that contains data node with key 'dVertex'\
        and content 'shallowHistory'.
    """

    ...


@dataclass
class CGMLDeepHistory(CGMLBaseVertex):
    """
    Data class with information about deep history node (pseudo node).

    DeepHistory is <node>, that contains data node with key 'dVertex'\
        and content 'deepHistory'.
    """

    ...


@dataclass
class CGMLEntryPoint(CGMLBaseVertex):
    """An entry point of a state or a submachine state (dVertex entryPoint)."""

    ...


@dataclass
class CGMLExitPoint(CGMLBaseVertex):
    """An exit point of a state or a submachine state (dVertex exitPoint)."""

    ...


@dataclass
class CGMLChoice(CGMLBaseVertex):
    """
    Data class with information about choice node (pseudo node).

    Choice is <node>, that contains data node with key 'dVertex'
    and content 'choice'.
    """

    ...


@dataclass
class CGMLTransition:
    """
    Data class with information about transition(<edge>).

    Parameters:
    source: <edge> source property's content.
    target: <edge> target property's content.
    actions: content of data node with 'dData' key.
    color: content of data node with 'dColor' key.
    position: x, y properties of data node with 'dGeometry' key.
    unknownDatanodes: all datanodes, whose information is not included.
    """

    id: str
    source: str
    target: str
    actions: str
    unknown_datanodes: List[CGMLDataNode]
    color: Optional[str] = None
    position: List[Point] = Field(default_factory=list)
    label_position: Optional[Union[Point, Rectangle]] = None
    pivot: Optional[str] = None
    source_point: Optional[Point] = None
    target_point: Optional[Point] = None


@dataclass
class CGMLLink:
    """
    A comment link: an edge from a comment to a node or a transition.

    pivot, chunk: dPivot, dChunk; position: the polyline;
    unknown_datanodes: the extension data.
    """

    id: str
    source: str
    target: str
    pivot: Optional[str] = None
    chunk: Optional[str] = None
    position: List[Point] = Field(default_factory=list)
    source_point: Optional[Point] = None
    target_point: Optional[Point] = None
    unknown_datanodes: List[CGMLDataNode] = Field(default_factory=list)


@dataclass
class CGMLFunction:
    """Data class with information about function."""

    id: str
    type: str
    parameters: Dict[str, str]
    inputs: Dict[str, CGMLInput]
    outputs: Dict[str, CGMLOutput]
    edges: Dict[str, CGMLTransition]
    body: Dict[str, CGMLBlock]
    name: Optional[str]


@dataclass
class CGMLNote:
    """
    Dataclass with infromation about note.

    Note is <node> containing data node with key 'dNote'
    type: content of <data key="dNote">
    text: content of <data key="dData">
    name: content of <data key="dName">
    position: properties <data key="dGeometry">'s child <point> or <rect>,
              None for a comment without geometry
    unknownDatanodes: all datanodes, whose information is not included.
    """

    name: str
    position: Optional[Union[Point, Rectangle]]
    text: str
    type: str
    unknown_datanodes: List[CGMLDataNode]
    parent: Optional[str] = None
    formal_name: Optional[str] = None
    markup: Optional[str] = None
    color: Optional[str] = None
    region: Optional[str] = None


@dataclass
class CGMLMeta:
    """
    The type represents meta-information\
    from formal note with 'dName' CGML_META.

    id: meta-node id.
    values: information from meta node, exclude required parameters.
    """

    id: str
    values: Dict[str, str]
    unknown_datanodes: List[CGMLDataNode] = Field(default_factory=list)


@dataclass
class CGMLFinal(CGMLBaseVertex):
    """
    The type represents final-states.

    Final state - <node>, that includes dVertex with content 'final'.
    """

    ...


@dataclass
class CGMLTerminate(CGMLBaseVertex):
    """
    The type represents terminate-states.

    Final state - <node>, that includes dVertex with content 'terminate'.
    """

    ...


@dataclass
class CGMLStateMachine:
    """
    The type represents state machine <graph>.

    Contains dict of CGMLStates, where the key is state's id.
    Also contains trainstions, components, awaialable keys, notes.

    States doesn't contains components nodes and pseudo-nodes.
    transitions doesn't contains component's transitions.
    """

    platform: str
    meta: CGMLMeta
    standard_version: str
    states: Dict[str, CGMLState]
    transitions: Dict[str, CGMLTransition]
    components: Dict[str, CGMLComponent]
    notes: Dict[str, CGMLNote]
    initial_states: Dict[str, CGMLInitialState]
    finals: Dict[str, CGMLFinal]
    choices: Dict[str, CGMLChoice]
    terminates: Dict[str, CGMLTerminate]
    shallow_history: Dict[str, CGMLShallowHistory]
    deep_history: Dict[str, CGMLDeepHistory]
    unknown_vertexes: Dict[str, CGMLBaseVertex]
    name: Optional[str] = Field(default=None)
    formal_name: Optional[str] = None
    bounds: Optional[Rectangle] = None
    links: Dict[str, CGMLLink] = Field(default_factory=dict)
    entry_points: Dict[str, CGMLEntryPoint] = Field(default_factory=dict)
    exit_points: Dict[str, CGMLExitPoint] = Field(default_factory=dict)
    unknown_datanodes: List[CGMLDataNode] = Field(default_factory=list)


class CGMLElements(BaseModel):
    """
    Dataclass with elements of parsed scheme.

    Parameters:
    meta: content of data node with key 'dData' inside meta-node.
    format: content of data node with key 'gFormat'.
    platform: content of meta-data
    keys: dict of KeyNodes, where the key is 'for' attribute.
    """

    state_machines: Dict[str, CGMLStateMachine]
    format: str
    keys: AvailableKeys
    functions: Dict[str, CGMLFunction]


Vertex = Union[
    CGMLFinal,
    CGMLChoice,
    CGMLInitialState,
    CGMLTerminate,
    CGMLShallowHistory,
    CGMLDeepHistory,
    CGMLEntryPoint,
    CGMLExitPoint,
    CGMLBaseVertex
]
