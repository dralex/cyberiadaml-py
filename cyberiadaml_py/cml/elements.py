# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The elements of the CyberiadaML interface
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
"""The element tree: the classes of the binding with its getters and dump."""
from typing import Iterable, List, Optional

from .actions import Action
from .enums import (CommentSubjectType, ElementType, TransitionType,
                    commentSubjectData, commentSubjectElement,
                    commentSubjectName, elementChoice, elementComment,
                    elementCompositeState, elementDeepHistory,
                    elementEntryPoint, elementExitPoint, elementFinal,
                    elementFormalComment, elementInitial,
                    elementShallowHistory, elementSimpleState,
                    elementSubmachineState, elementTerminate,
                    elementTransition, transitionExternal,
                    QUALIFIED_NAME_SEPARATOR)
from .geometry import Point, Polyline, Rect

TYPE_NAMES = {
    ElementType.elementRoot: 'Document',
    ElementType.elementSM: 'State Machine',
    ElementType.elementSimpleState: 'Simple State',
    ElementType.elementCompositeState: 'Composite State',
    ElementType.elementComment: 'Comment',
    ElementType.elementFormalComment: 'Formal Comment',
    ElementType.elementInitial: 'Initial',
    ElementType.elementFinal: 'Final',
    ElementType.elementChoice: 'Choice',
    ElementType.elementTerminate: 'Terminate',
    ElementType.elementShallowHistory: 'Shallow History',
    ElementType.elementDeepHistory: 'Deep History',
    ElementType.elementSubmachineState: 'Submachine State',
    ElementType.elementEntryPoint: 'Entry Point',
    ElementType.elementExitPoint: 'Exit Point',
    ElementType.elementTransition: 'Transition',
}
SUBJECT_NAMES = {commentSubjectElement: 'element', commentSubjectName: 'name',
                 commentSubjectData: 'data'}
VERTEX_TYPES = (elementSimpleState, elementCompositeState, elementInitial,
                elementFinal, elementChoice, elementTerminate,
                elementShallowHistory, elementDeepHistory, elementEntryPoint,
                elementExitPoint)
STATE_TYPES = (elementSimpleState, elementCompositeState)
COMMENT_TYPES = (elementComment, elementFormalComment)


def _point(value: Optional[Point]) -> Point:
    return value.copy() if value is not None else Point()


def _rect(value: Optional[Rect]) -> Rect:
    return value.copy() if value is not None else Rect()


class Element:
    """An element of the document tree."""

    def __init__(self, parent: Optional['Element'], type_: ElementType,
                 id_: str, name: Optional[str] = None) -> None:
        self._parent = parent
        self._type = ElementType(type_)
        self._id = id_
        self._name = name
        self._formal_name: Optional[str] = None

    def get_id(self) -> str:
        return self._id

    def get_name(self) -> str:
        return self._name if self._name is not None else ''

    def has_name(self) -> bool:
        return self._name is not None

    def get_formal_name(self) -> str:
        return self._formal_name if self._formal_name is not None else ''

    def has_formal_name(self) -> bool:
        return self._formal_name is not None

    def get_qualified_name(self) -> str:
        parent = self._parent
        if parent is None or parent._parent is None or \
                parent._parent._parent is None:
            return self.get_name()
        return parent.get_qualified_name() + QUALIFIED_NAME_SEPARATOR + \
            self.get_name()

    def has_qualified_name(self) -> bool:
        return self._parent is None or self.has_name() or \
            self._parent.has_qualified_name()

    def get_full_qualified_name(self) -> str:
        parent = self._parent
        if parent is None or parent._parent is None:
            return self.get_name()
        return parent.get_full_qualified_name() + \
            QUALIFIED_NAME_SEPARATOR + self.get_name()

    def get_type(self) -> ElementType:
        return self._type

    def get_parent(self) -> Optional['Element']:
        return self._parent

    def is_root(self) -> bool:
        return self._parent is None

    def index(self) -> int:
        if isinstance(self._parent, ElementCollection):
            return self._parent.element_index(self)
        return 0

    get_index = index

    def has_children(self) -> bool:
        return False

    def get_children_count(self) -> int:
        return 0

    def get_elements_count(self) -> int:
        return 1

    def has_geometry(self) -> bool:
        return False

    def _prefix(self) -> str:
        text = "%s: {id: '%s'" % (TYPE_NAMES[self._type], self._id)
        if self._name is not None:
            text += ", name: '%s'" % self._name
        if self._formal_name is not None:
            text += ", formal name: '%s'" % self._formal_name
        return text

    def __repr__(self) -> str:
        return self._prefix() + '}'


class CommentSubject:
    """What a comment comments: an element, its name or its data."""

    def __init__(self, id_: str, element: Element, *args, **kwargs) -> None:
        self._id = id_
        self._element = element
        self._type = commentSubjectElement
        self._fragment: Optional[str] = None
        if args and isinstance(args[0], CommentSubjectType):
            self._type, self._fragment = args[0], args[1]
            args = args[2:]
        elif 'type' in kwargs:
            self._type = CommentSubjectType(kwargs.pop('type'))
            self._fragment = kwargs.pop('fragment')
        names = ('source', 'target', 'polyline')
        values = dict(zip(names, args), **kwargs)
        self._source = _point(values.get('source'))
        self._target = _point(values.get('target'))
        polyline = values.get('polyline')
        self._polyline = polyline.copy() if polyline is not None \
            else Polyline()

    def get_id(self) -> str:
        return self._id

    def get_type(self) -> CommentSubjectType:
        return self._type

    def get_element(self) -> Element:
        return self._element

    def has_fragment(self) -> bool:
        return self._fragment is not None

    def get_fragment(self) -> str:
        return self._fragment or ''

    def has_geometry(self) -> bool:
        return self._source.valid or self._target.valid or \
            len(self._polyline) > 0

    def has_geometry_source_point(self) -> bool:
        return self._source.valid

    def get_geometry_source_point(self) -> Point:
        return self._source

    def has_geometry_target_point(self) -> bool:
        return self._target.valid

    def get_geometry_target_point(self) -> Point:
        return self._target

    def has_geometry_polyline(self) -> bool:
        return len(self._polyline) > 0

    def get_geometry_polyline(self) -> Polyline:
        return self._polyline

    def __repr__(self) -> str:
        text = "{id: '%s', type: %s" % (self._id, SUBJECT_NAMES[self._type])
        if self._element is not None:
            text += ", to: '%s'" % self._element.get_id()
            if self._fragment is not None:
                text += ", fragment: '%s'" % self._fragment
            if self._source.valid:
                text += ', source point: %r' % self._source
            if self._target.valid:
                text += ', target point: %r' % self._target
            if len(self._polyline):
                text += ', polyline: %r' % self._polyline
        return text + '}'


class Comment(Element):
    """A comment.

    Comment(parent, id, body[, name], human_readable=True, markup='',
    rect=Rect(), color='').
    """

    def __init__(self, parent: Optional[Element], id_: str, body: str,
                 *args, **kwargs) -> None:
        name = None
        if args and isinstance(args[0], str):
            name, args = args[0], args[1:]
        elif 'name' in kwargs:
            name = kwargs.pop('name')
        names = ('human_readable', 'markup', 'rect', 'color')
        values = dict(zip(names, args), **kwargs)
        human = values.get('human_readable', True)
        super().__init__(parent, elementComment if human
                         else elementFormalComment, id_, name)
        self._body = body
        self._markup = values.get('markup', '') or ''
        self._rect = _rect(values.get('rect'))
        self._color = values.get('color', '') or ''
        self._subjects: List[CommentSubject] = []

    def get_body(self) -> str:
        return self._body

    def has_body(self) -> bool:
        return bool(self._body)

    def get_markup(self) -> str:
        return self._markup

    def has_markup(self) -> bool:
        return bool(self._markup)

    def get_color(self) -> str:
        return self._color

    def has_color(self) -> bool:
        return bool(self._color)

    def is_human_readable(self) -> bool:
        return self._type == elementComment

    def is_machine_readable(self) -> bool:
        return self._type == elementFormalComment

    def get_geometry_rect(self) -> Rect:
        return self._rect.copy()

    def has_geometry(self) -> bool:
        return self._rect.valid

    def has_subjects(self) -> bool:
        return bool(self._subjects)

    def get_subjects(self) -> List[CommentSubject]:
        return self._subjects

    def __repr__(self) -> str:
        text = self._prefix() + ", body: '%s'" % self._body
        if self._rect.valid:
            text += ', geometry: %r' % self._rect
        if self._subjects:
            text += ', subjects: {%s}' % ', '.join(
                repr(s) for s in self._subjects)
        return text + '}'


class Vertex(Element):
    """A vertex with a point geometry."""

    def __init__(self, parent: Optional[Element], type_: ElementType,
                 id_: str, name: Optional[str] = None,
                 point: Optional[Point] = None, color: str = '') -> None:
        super().__init__(parent, type_, id_, name)
        self._point = _point(point)
        self._color = color or ''

    def get_geometry_point(self) -> Point:
        return self._point

    def has_geometry(self) -> bool:
        return self._point.valid

    def __repr__(self) -> str:
        text = self._prefix()
        if self._point.valid:
            text += ', geometry: %r' % self._point
        if self._color:
            text += ', color: %s' % self._color
        return text + '}'


class Pseudostate(Vertex):
    """A pseudostate."""


def _named(args: tuple, kwargs: dict, names: tuple) -> tuple:
    """Split the optional name off the arguments of a vertex constructor."""
    name = None
    if args and isinstance(args[0], str):
        name, args = args[0], args[1:]
    elif 'name' in kwargs:
        name = kwargs.pop('name')
    return name, dict(zip(names, args), **kwargs)


class Initial(Pseudostate):
    """Initial(parent, id[, name], point=Point())."""

    def __init__(self, parent: Optional[Element], id_: str, *args,
                 **kwargs) -> None:
        name, values = _named(args, kwargs, ('point', 'color'))
        super().__init__(parent, elementInitial, id_, name,
                         values.get('point'), values.get('color', ''))


class Terminate(Pseudostate):
    """Terminate(parent, id[, name], point=Point())."""

    def __init__(self, parent: Optional[Element], id_: str, *args,
                 **kwargs) -> None:
        name, values = _named(args, kwargs, ('point', 'color'))
        super().__init__(parent, elementTerminate, id_, name,
                         values.get('point'), values.get('color', ''))


class Final(Vertex):
    """Final(parent, id[, name], point=Point())."""

    def __init__(self, parent: Optional[Element], id_: str, *args,
                 **kwargs) -> None:
        name, values = _named(args, kwargs, ('point', 'color'))
        super().__init__(parent, elementFinal, id_, name,
                         values.get('point'), values.get('color', ''))


class History(Pseudostate):
    """History(parent, type, id[, name], point=Point(), color='')."""

    def __init__(self, parent: Optional[Element], type_: ElementType,
                 id_: str, *args, **kwargs) -> None:
        name, values = _named(args, kwargs, ('point', 'color'))
        super().__init__(parent, type_, id_, name, values.get('point'),
                         values.get('color', ''))


class ConnectionPoint(Pseudostate):
    """ConnectionPoint(parent, type, id[, name], point=Point(), color='')."""

    def __init__(self, parent: Optional[Element], type_: ElementType,
                 id_: str, *args, **kwargs) -> None:
        name, values = _named(args, kwargs, ('point', 'color'))
        super().__init__(parent, type_, id_, name, values.get('point'),
                         values.get('color', ''))


class Choice(Pseudostate):
    """Choice(parent, id[, name], rect=Rect(), color='')."""

    def __init__(self, parent: Optional[Element], id_: str, *args,
                 **kwargs) -> None:
        name, values = _named(args, kwargs, ('rect', 'color'))
        super().__init__(parent, elementChoice, id_, name, None,
                         values.get('color', ''))
        self._rect = _rect(values.get('rect'))

    def get_geometry_rect(self) -> Rect:
        return self._rect

    def has_geometry(self) -> bool:
        return self._rect.valid

    def get_color(self) -> str:
        return self._color

    def has_color(self) -> bool:
        return bool(self._color)

    def __repr__(self) -> str:
        text = self._prefix()
        if self._rect.valid:
            text += ', geometry: %r' % self._rect
            if self._color:
                text += ', color: %s' % self._color
        return text + '}'


class Transition(Element):
    """A transition; source and target are element ids.

    Transition(parent, ttype, id, source, target, action, polyline, sp, tp,
    label_point, label_rect, color).
    """

    def __init__(self, parent: Optional[Element], ttype: TransitionType,
                 id_: str, source: str, target: str,
                 action: Optional[Action] = None,
                 polyline: Optional[Polyline] = None,
                 sp: Optional[Point] = None, tp: Optional[Point] = None,
                 label_point: Optional[Point] = None,
                 label_rect: Optional[Rect] = None,
                 color: str = '') -> None:
        super().__init__(parent, elementTransition, id_)
        self._ttype = TransitionType(ttype)
        self._source, self._target = source, target
        self._action = action.copy() if action is not None else Action()
        self._polyline = polyline.copy() if polyline is not None \
            else Polyline()
        self._sp, self._tp = _point(sp), _point(tp)
        self._label_point = _point(label_point)
        self._label_rect = _rect(label_rect)
        self._color = color or ''

    def get_transition_type(self) -> TransitionType:
        return self._ttype

    def get_source_element_id(self) -> str:
        return self._source

    def get_target_element_id(self) -> str:
        return self._target

    def get_action(self) -> Action:
        return self._action

    def has_action(self) -> bool:
        return self._action.has_trigger() or self._action.has_guard() or \
            self._action.has_behavior()

    def get_color(self) -> str:
        return self._color

    def has_color(self) -> bool:
        return bool(self._color)

    def has_geometry(self) -> bool:
        return self._sp.valid or self._tp.valid or \
            self._label_point.valid or self._label_rect.valid or \
            len(self._polyline) > 0

    def has_geometry_polyline(self) -> bool:
        return len(self._polyline) > 0

    def get_geometry_polyline(self) -> Polyline:
        return self._polyline

    def has_geometry_source_point(self) -> bool:
        return self._sp.valid

    def get_geometry_source_point(self) -> Point:
        return self._sp

    def has_geometry_target_point(self) -> bool:
        return self._tp.valid

    def get_geometry_target_point(self) -> Point:
        return self._tp

    def has_geometry_label_point(self) -> bool:
        return self._label_point.valid

    def get_geometry_label_point(self) -> Point:
        return self._label_point

    def has_geometry_label_rect(self) -> bool:
        return self._label_rect.valid

    def get_geometry_label_rect(self) -> Rect:
        return self._label_rect

    def __repr__(self) -> str:
        text = self._prefix() + ', type: %s' % (
            'ext' if self._ttype == transitionExternal else 'loc')
        text += ", source: '%s', target: '%s'" % (self._source, self._target)
        if self.has_action():
            text += ', action: {%r}' % self._action
        if self.has_geometry():
            if self._sp.valid:
                text += ', sp: %r' % self._sp
            if self._tp.valid:
                text += ', tp: %r' % self._tp
            if self._label_point.valid:
                text += ', label: %r' % self._label_point
            elif self._label_rect.valid:
                text += ', rect: %r' % self._label_rect
            if len(self._polyline):
                text += ', polyline: %r' % self._polyline
            if self._color:
                text += ', color: %s' % self._color
        return text + '}'


class ElementCollection(Element):
    """An element with children: a state, a state machine, the document."""

    def __init__(self, parent: Optional[Element], type_: ElementType,
                 id_: str, name: Optional[str] = None,
                 rect: Optional[Rect] = None, color: str = '') -> None:
        super().__init__(parent, type_, id_, name)
        self._children: List[Element] = []
        self._rect = _rect(rect)
        self._color = color or ''

    def _attach(self, element: Element) -> None:
        """Add a child; transitions go after every other element."""
        element._parent = self
        if element.get_type() == elementTransition:
            self._children.append(element)
        else:
            index = next((i for i, e in enumerate(self._children)
                          if e.get_type() == elementTransition),
                         len(self._children))
            self._children.insert(index, element)

    def has_children(self) -> bool:
        return bool(self._children)

    def children_count(self) -> int:
        return len(self._children)

    get_children_count = children_count

    def elements_count(self) -> int:
        return 1 + sum(e.get_elements_count() for e in self._children)

    get_elements_count = elements_count

    def get_children(self) -> List[Element]:
        return list(self._children)

    def get_element(self, index: int) -> Optional[Element]:
        if 0 <= index < len(self._children):
            return self._children[index]
        return None

    def first_element(self) -> Optional[Element]:
        return self._children[0] if self._children else None

    def element_index(self, element: Element) -> int:
        for index, child in enumerate(self._children):
            if child is element:
                return index
        return -1

    def find_element_by_id(self, id_: str) -> Optional[Element]:
        for child in self._children:
            if child.get_id() == id_:
                return child
            if isinstance(child, ElementCollection) and child.has_children():
                found = child.find_element_by_id(id_)
                if found is not None:
                    return found
        return None

    def find_elements_by_types(self, types: Iterable[ElementType]) \
            -> List[Element]:
        wanted = set(types)
        result: List[Element] = []
        for child in self._children:
            if child.get_type() in wanted:
                result.append(child)
            if isinstance(child, ElementCollection):
                result.extend(child.find_elements_by_types(wanted))
        return result

    def find_elements_by_type(self, type_: ElementType) -> List[Element]:
        return self.find_elements_by_types([type_])

    def get_vertexes(self) -> List[Element]:
        return self.find_elements_by_types(VERTEX_TYPES)

    def has_initial(self) -> bool:
        return any(e.get_type() == elementInitial for e in self._children)

    def get_geometry_rect(self) -> Rect:
        return self._rect

    def has_geometry(self) -> bool:
        return self._rect.valid

    def get_color(self) -> str:
        return self._color

    def has_color(self) -> bool:
        return bool(self._color)

    def _collection(self) -> str:
        text = ''
        if self._rect.valid:
            text += ', geometry: %r' % self._rect
            if self._color:
                text += ', color: %s' % self._color
        if self._children:
            text += ', elements: {%s}' % ', '.join(
                repr(e) for e in self._children)
        return text

    def __repr__(self) -> str:
        return self._prefix() + self._collection() + '}'


class State(ElementCollection):
    """State(parent, id, name, rect=Rect(), region_rect=Rect(), color='')."""

    def __init__(self, parent: Optional[Element], id_: str, name: str,
                 rect: Optional[Rect] = None,
                 region_rect: Optional[Rect] = None,
                 color: str = '') -> None:
        super().__init__(parent, elementSimpleState, id_, name, rect, color)
        self._actions: List[Action] = []
        self._region_rect = _rect(region_rect)
        self._collapsed = False

    def _attach(self, element: Element) -> None:
        super()._attach(element)
        self._update_type()

    def _update_type(self) -> None:
        if self._type in STATE_TYPES:
            self._type = elementCompositeState if self._children \
                else elementSimpleState

    def has_actions(self) -> bool:
        return bool(self._actions)

    def get_actions(self) -> List[Action]:
        return [a.copy() for a in self._actions]

    def is_simple_state(self) -> bool:
        return self._type == elementSimpleState

    def is_composite_state(self) -> bool:
        return self._type == elementCompositeState

    def get_substates(self) -> List[Element]:
        return self.find_elements_by_types(STATE_TYPES)

    def is_collapsed(self) -> bool:
        return self._collapsed

    def has_region_geometry(self) -> bool:
        return self._region_rect.valid

    def get_region_geometry_rect(self) -> Rect:
        return self._region_rect.copy()

    def __repr__(self) -> str:
        text = self._prefix()
        if self._actions:
            text += ', actions: {%s}' % ', '.join(
                'a {%r}' % a for a in self._actions)
        text += self._collection()
        if self._region_rect.valid:
            text += ', region: %r' % self._region_rect
        return text + '}'


class SubmachineState(State):
    """SubmachineState(parent, id, name, reference, rect=Rect(), color='')."""

    def __init__(self, parent: Optional[Element], id_: str, name: str,
                 reference: str, rect: Optional[Rect] = None,
                 color: str = '') -> None:
        super().__init__(parent, id_, name, rect, None, color)
        self._type = elementSubmachineState
        self._reference = reference

    def is_submachine_state(self) -> bool:
        return True

    def get_submachine_reference(self) -> str:
        return self._reference

    def __repr__(self) -> str:
        return self._prefix() + ", submachine: '%s'" % self._reference + \
            self._collection() + '}'


class StateMachine(ElementCollection):
    """StateMachine(parent, id, name='', rect=Rect())."""

    def __init__(self, parent: Optional[Element], id_: str, name: str = '',
                 rect: Optional[Rect] = None) -> None:
        super().__init__(parent, ElementType.elementSM, id_, name, rect)

    def get_comments(self) -> List[Element]:
        return self.find_elements_by_types(COMMENT_TYPES)

    def get_transitions(self) -> List[Element]:
        return self.find_elements_by_type(elementTransition)
