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
import copy as copying
from typing import Iterable, List, Optional

from . import errors
from .actions import Action
from .enums import (CommentSubjectType, ElementType, TransitionType,
                    actionTransition, adiffActions, adiffArguments,
                    adiffGuards, adiffNumber, adiffOrder, adiffPropagation,
                    adiffTypes,
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


def _subtree(element: 'Element') -> List['Element']:
    result = [element]
    for child in getattr(element, '_children', []):
        result.extend(_subtree(child))
    return result


# the action types of the C library are bits, for the types mask
ACTION_BITS = {0: 0x1, 1: 0x2, 2: 0x4}


def _arguments_differ(command1: str, command2: str) -> bool:
    bracket = False
    for char1, char2 in zip(command1, command2):
        if char1 == char2:
            if not bracket and char1 == '(':
                bracket = True
        elif not bracket:
            return False
        else:
            return True
    return False


def _compare_behaviors(behavior1: str, behavior2: str) -> int:
    commands1 = behavior1.split('\n')
    commands2 = behavior2.split('\n')
    flags = adiffActions if len(commands1) != len(commands2) else 0
    for i, command in enumerate(commands1):
        for j, other in enumerate(commands2):
            if not other:
                continue
            if command == other:
                if i != j:
                    flags |= adiffOrder
                commands2[j] = ''
                break
            if _arguments_differ(command, other):
                flags |= adiffArguments
                commands2[j] = ''
    if any(commands2):
        flags |= adiffActions
    return flags


def compare_action_lists(list1: List[Action], list2: List[Action]) -> int:
    """Return the adiff flags of two action lists, as the C library does."""
    list1 = [a for a in list1 if not a.is_empty_transition() or
             a.get_type() != actionTransition]
    list2 = [a for a in list2 if not a.is_empty_transition() or
             a.get_type() != actionTransition]
    if not list1 and not list2:
        return 0
    if not list1 or not list2:
        return adiffActions | adiffTypes | adiffNumber
    flags = adiffNumber if len(list1) != len(list2) else 0
    types1 = types2 = 0
    for action in list1:
        types1 |= ACTION_BITS[int(action.get_type())]
    for action in list2:
        types2 |= ACTION_BITS[int(action.get_type())]
    if types1 != types2:
        flags |= adiffTypes
    for a1 in list1:
        found = False
        for a2 in list2:
            if a1.get_type() != a2.get_type() or \
                    (a2.get_type() == actionTransition and
                     a1.get_trigger() != a2.get_trigger()):
                continue
            if a1.get_guard() == a2.get_guard():
                found = True
                if a1.get_propagation() != a2.get_propagation():
                    flags |= adiffPropagation
                if a1.get_behavior() != a2.get_behavior():
                    flags |= _compare_behaviors(a1.get_behavior(),
                                                a2.get_behavior())
                break
            if a1.get_behavior() == a2.get_behavior():
                flags |= adiffGuards
        if not found:
            return flags | adiffActions
    return flags


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

    def set_id(self, id_: str) -> None:
        self._id = id_

    def set_name(self, name: str) -> None:
        self._name = name

    def set_formal_name(self, name: str) -> None:
        self._formal_name = name
        if self._name is None:
            self._name = name

    def clean_geometry(self) -> None:
        pass

    def round_geometry(self) -> None:
        pass

    def copy(self, parent: Optional['Element']) -> 'Element':
        """Return a detached deep copy with the same ids under parent."""
        # the subjects keep the targets outside the copy, as the C++ does
        inside = {id(element) for element in _subtree(self)}
        memo = {id(self._parent): parent}
        for element in _subtree(self):
            for subject in getattr(element, '_subjects', []):
                if id(subject._element) not in inside:
                    memo.setdefault(id(subject._element), subject._element)
        result = copying.deepcopy(self, memo)
        result._parent = parent
        return result

    def get_bound_rect(self, d) -> Rect:
        return Rect()

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

    def get_bound_rect(self, d) -> Rect:
        r = Rect()
        if self.has_geometry() and len(self._polyline):
            r.expand(self._polyline, d)
        return r

    def get_geometry_polyline(self) -> Polyline:
        return self._polyline

    def clean_geometry(self) -> None:
        self._source, self._target = Point(), Point()
        self._polyline = Polyline()

    def round_geometry(self) -> None:
        self._source.round()
        self._target.round()
        self._polyline.round()

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

    def get_bound_rect(self, d) -> Rect:
        r = parent_rect = Rect()
        if self.has_geometry():
            r = self._rect.copy()
            parent_rect = self._rect.copy()
            for subject in self._subjects:
                element = subject.get_element()
                if element is None or not element.has_geometry():
                    continue
                ch = subject.get_bound_rect(d)
                if int(d.get_geometry_format()) in (CYB_FORMAT,
                                                    QT_FORMAT):
                    ch.x += parent_rect.x
                    ch.y += parent_rect.y
                r.expand(ch, d)
        return r

    def has_subjects(self) -> bool:
        return bool(self._subjects)

    def get_subjects(self) -> List[CommentSubject]:
        return self._subjects

    def set_body(self, body: str) -> None:
        self._body = body

    def update_geometry(self, rect: Rect) -> None:
        self._rect = rect.copy()

    def clean_geometry(self) -> None:
        self._rect = Rect()
        for subject in self._subjects:
            subject.clean_geometry()

    def round_geometry(self) -> None:
        self._rect.round()
        for subject in self._subjects:
            subject.round_geometry()

    def add_subject(self, subject: CommentSubject) -> CommentSubject:
        self._subjects.append(copying.copy(subject))
        return self._subjects[-1]

    def _subject_at(self, index: int) -> CommentSubject:
        if not 0 <= index < len(self._subjects):
            raise errors.error(errors.ParametersException,
                               'Bad comment subject index')
        return self._subjects[index]

    def update_subject(self, index: int,
                       subject: CommentSubject) -> CommentSubject:
        self._subject_at(index)
        self._subjects[index] = copying.copy(subject)
        return copying.copy(self._subjects[index])

    def update_subject_geometry(self, index: int, source: Point,
                                target: Optional[Point] = None,
                                polyline: Optional[Polyline] = None) -> None:
        # a fragment subject keeps no target point (PNST 1044 9.1.1)
        s = self._subject_at(index)
        s._source = _point(source)
        s._target = Point() if s.has_fragment() else _point(target)
        s._polyline = polyline.copy() if polyline is not None \
            else Polyline()

    def remove_subject(self, *args) -> None:
        if len(args) == 1 and not isinstance(args[0], CommentSubjectType):
            index = args[0]
            if not 0 <= index < len(self._subjects):
                raise errors.error(errors.ParametersException,
                                   'Bad subject index %d' % index)
            del self._subjects[index]
            return
        kind, fragment = args
        for index, subject in enumerate(self._subjects):
            if subject.get_type() == kind and \
                    subject.get_fragment() == fragment:
                del self._subjects[index]
                return
        raise errors.error(errors.NotFoundException,
                           'No subject with the fragment %s' % fragment)

    def rebind_subjects(self, root: 'ElementCollection') -> None:
        for subject in self._subjects:
            target = subject._element.get_id()
            element = root.find_element_by_id(target)
            if element is None and root.get_id() == target:
                element = root
            if element is not None:
                subject._element = element

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

    def get_bound_rect(self, d) -> Rect:
        r = Rect()
        if self.has_geometry():
            r.expand(self._point, d)
        return r

    def update_geometry(self, point: Point) -> None:
        self._point = point.copy()

    def clean_geometry(self) -> None:
        self._point = Point()

    def round_geometry(self) -> None:
        self._point.round()

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

    def get_bound_rect(self, d) -> Rect:
        return self._rect.copy() if self.has_geometry() else Rect()

    def get_color(self) -> str:
        return self._color

    def has_color(self) -> bool:
        return bool(self._color)

    def update_geometry(self, rect: Rect) -> None:  # type: ignore[override]
        self._rect = rect.copy()

    def clean_geometry(self) -> None:
        self._rect = Rect()

    def round_geometry(self) -> None:
        self._rect.round()

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

    def get_bound_rect(self, d) -> Rect:
        r = Rect()
        if self.has_geometry() and len(self._polyline):
            r.expand(self._polyline, d)
        return r

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

    def compare_actions(self, transition: 'Transition') -> int:
        return compare_action_lists([self._action], [transition._action])

    def update(self, *args) -> None:
        if len(args) == 1:
            self._polyline = args[0].copy()
        elif isinstance(args[0], str):
            self._source, self._target = args
        else:
            self._sp, self._tp = args[0].copy(), args[1].copy()

    def update_label(self, label) -> None:
        if isinstance(label, Rect):
            self._label_point = Point()
            self._label_rect = label.copy()
        else:
            self._label_rect = Rect()
            self._label_point = label.copy()

    def clean_geometry(self) -> None:
        self._sp, self._tp, self._label_point = Point(), Point(), Point()
        self._label_rect, self._polyline = Rect(), Polyline()

    def round_geometry(self) -> None:
        for value in (self._sp, self._tp, self._label_point,
                      self._label_rect, self._polyline):
            value.round()

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


CYB_FORMAT = 2              # geometryFormatCyberiada10
QT_FORMAT = 3               # geometryFormatQt
YED_FORMAT = 1              # geometryFormatLegacyYED


def _own_position(element: Element):
    # the stored position (and size for the rect-based elements)
    if isinstance(element, (ElementCollection, Choice, Comment)):
        r = element._rect
        return (r.x, r.y, r.width, r.height) if r.valid else None
    if isinstance(element, Vertex):
        p = element._point
        return (p.x, p.y, 0.0, 0.0) if p.valid else None
    return None


def _node_frame(coll: 'ElementCollection', node: Element, fmt: int):
    # the node frame relative to the frame of the parent of the collection
    own = _own_position(node)
    if own is None:
        return None
    fx, fy, w, h = own
    if fmt == YED_FORMAT:
        return fx, fy, w, h
    stop = coll.get_parent()
    e = node.get_parent()
    while e is not None and e is not stop:
        pos = _own_position(e)
        if pos is not None:
            fx += pos[0]
            fy += pos[1]
        # the children of a state with a region are relative to it
        if isinstance(e, State) and e.has_region_geometry():
            fx += e._region_rect.x
            fy += e._region_rect.y
        e = e.get_parent()
    return fx, fy, w, h


def _expand_transition(r: Rect, coll: 'ElementCollection', t: 'Transition',
                       d, fmt: int) -> None:
    """Extend the rect by the resolved geometry of a transition."""
    if not t.has_geometry():
        return
    source = d.find_element_by_id(t.get_source_element_id())
    target = d.find_element_by_id(t.get_target_element_id())
    if source is None or target is None:
        return
    sf = _node_frame(coll, source, fmt)
    tf = _node_frame(coll, target, fmt)
    if sf is None or tf is None:
        return
    sfx, sfy, sw, sh = sf
    tfx, tfy, tw, th = tf
    yed = fmt == YED_FORMAT
    # the explicit ends are bound to the centres (yed/qt) or the corners
    if t._sp.valid:
        sp = Point(sfx + sw / 2.0 + t._sp.x, sfy + sh / 2.0 + t._sp.y) \
            if yed else Point(sfx + t._sp.x, sfy + t._sp.y)
    elif fmt == QT_FORMAT:
        sp = Point(sfx, sfy)
    else:
        sp = Point(sfx + sw / 2.0, sfy + sh / 2.0)
    if t._tp.valid:
        tp = Point(tfx + tw / 2.0 + t._tp.x, tfy + th / 2.0 + t._tp.y) \
            if yed else Point(tfx + t._tp.x, tfy + t._tp.y)
    elif fmt == QT_FORMAT:
        tp = Point(tfx, tfy)
    else:
        tp = Point(tfx + tw / 2.0, tfy + th / 2.0)
    if len(t._polyline):
        r.expand(sp, d)
        r.expand(tp, d)
        for p in t._polyline:
            r.expand(p if yed else Point(sfx + p.x, sfy + p.y), d)
    # the labels always extend the rect
    if t._label_point.valid:
        lp = t._label_point
        r.expand(Point(sp.x + lp.x, sp.y + lp.y) if yed
                 else Point(sfx + lp.x, sfy + lp.y), d)
    if t._label_rect.valid:
        lr = t._label_rect
        if yed:
            r.expand(Rect(sfx + sw / 2.0 + lr.x - lr.width / 2.0,
                          sfy + sh / 2.0 + lr.y - lr.height / 2.0,
                          lr.width, lr.height), d)
        else:
            r.expand(Rect(sfx + lr.x, sfy + lr.y, lr.width, lr.height), d)


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

    def _check_child(self, element: Element) -> None:
        if not isinstance(element, Element):
            raise TypeError('an Element is expected')
        if element._parent is not self:
            raise errors.error(errors.AssertException,
                               'the element is created for another parent')

    def add_element(self, element: Element) -> None:
        self._check_child(element)
        self._attach(element)

    def add_first_element(self, element: Element) -> None:
        self._check_child(element)
        self._children.insert(0, element)

    def remove_element(self, id_: str) -> None:
        for index, child in enumerate(self._children):
            if child.get_id() == id_:
                del self._children[index]
                break

    def clear(self) -> None:
        self._children = []

    def rebind_subjects(self, root: 'ElementCollection') -> None:
        for element in _subtree(self):
            if isinstance(element, Comment):
                element.rebind_subjects(root)

    def update_geometry(self, rect: Rect) -> None:
        self._rect = rect.copy()

    def clean_geometry(self) -> None:
        self._rect = Rect()
        for child in self._children:
            child.clean_geometry()

    def round_geometry(self) -> None:
        self._rect.round()
        for child in self._children:
            child.round_geometry()

    def has_initial(self) -> bool:
        return any(e.get_type() == elementInitial for e in self._children)

    def get_geometry_rect(self) -> Rect:
        return self._rect

    def has_geometry(self) -> bool:
        return self._rect.valid

    def get_bound_rect(self, d, exclude_comments: bool = False) -> Rect:
        r = Rect()
        parent_rect = Rect()
        fmt = int(d.get_geometry_format())
        if self.has_geometry():
            parent_rect = self._rect.copy()
            r.expand(self._rect, d)
        for child in self._children:
            if isinstance(child, Transition):
                _expand_transition(r, self, child, d, fmt)
                continue
            # a comment may lie outside the state-machine border
            if exclude_comments and child.get_type() in COMMENT_TYPES:
                continue
            if isinstance(child, ElementCollection):
                ch = child._bound_rect(d, exclude_comments)
            else:
                ch = child.get_bound_rect(d)
            if fmt in (CYB_FORMAT, QT_FORMAT):
                ch.x += parent_rect.x
                ch.y += parent_rect.y
            r.expand(ch, d)
        return r

    def _bound_rect(self, d, exclude_comments: bool) -> Rect:
        return ElementCollection.get_bound_rect(self, d, exclude_comments)

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

    def update_region_geometry_rect(self, rect: Rect) -> None:
        self._region_rect = rect.copy()

    def set_collapsed(self, flag: bool) -> None:
        self._collapsed = bool(flag)

    def remove_element(self, id_: str) -> None:
        super().remove_element(id_)
        self._update_type()

    def clear(self) -> None:
        super().clear()
        self._update_type()

    def add_first_element(self, element: Element) -> None:
        super().add_first_element(element)
        self._update_type()

    def add_action(self, action: Action) -> None:
        if not isinstance(action, Action):
            raise TypeError('an Action is expected')
        if action.is_empty_transition():
            raise errors.error(errors.ParametersException,
                               'Empty transition action is not allowed')
        if action.get_type() != actionTransition and action.has_guard():
            raise errors.error(errors.ParametersException, 'Guards are not '
                               'allowed for entry/exit activities')
        self._actions.append(action.copy())

    def set_actions(self, actions: Iterable[Action]) -> None:
        actions = list(actions)
        if not all(isinstance(action, Action) for action in actions):
            # the binding's list conversion fails this way
            raise RuntimeError('Unable to cast the list item to Action')
        saved = self._actions
        self._actions = []
        try:
            for action in actions:
                self.add_action(action)
        except BaseException:
            self._actions = saved
            raise

    def clear_actions(self) -> None:
        self._actions = []

    def remove_action(self, index: int) -> None:
        if not 0 <= index < len(self._actions):
            raise errors.error(errors.ParametersException,
                               'Bad action index %d' % index)
        del self._actions[index]

    def compare_actions(self, state: 'State') -> int:
        return compare_action_lists(self._actions, state._actions)

    def clean_geometry(self) -> None:
        self._region_rect = Rect()
        super().clean_geometry()

    def round_geometry(self) -> None:
        self._region_rect.round()
        super().round_geometry()

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

    def set_submachine_reference(self, reference: str) -> None:
        self._reference = reference

    def __repr__(self) -> str:
        return self._prefix() + ", submachine: '%s'" % self._reference + \
            self._collection() + '}'


class StateMachine(ElementCollection):
    """StateMachine(parent, id, name='', rect=Rect()) or StateMachine(sm)."""

    def __init__(self, parent, id_: str = '', name: str = '',
                 rect: Optional[Rect] = None) -> None:
        if isinstance(parent, StateMachine):
            source = parent.copy(parent._parent)
            self.__dict__.update(source.__dict__)
            for child in self._children:
                child._parent = self
            return
        super().__init__(parent, ElementType.elementSM, id_, name, rect)

    def check_isomorphism(self, machine: 'StateMachine',
                          ignore_comments: bool = True,
                          require_initial: bool = False) -> int:
        """Return smiIdentical for an identical machine; no more."""
        from .enums import smiIdentical

        def text(sm: 'StateMachine') -> str:
            copy = sm.copy(None)
            if ignore_comments:
                for element in _subtree(copy):
                    if isinstance(element, ElementCollection):
                        element._children = [
                            c for c in element._children
                            if c.get_type() not in COMMENT_TYPES]
            return repr(copy)

        if text(self) == text(machine):
            return smiIdentical
        raise errors.error(errors.NotImplementedException,
                           'the isomorphism of different machines')

    def get_comments(self) -> List[Element]:
        return self.find_elements_by_types(COMMENT_TYPES)

    def get_bound_rect(self, d,                    # type: ignore[override]
                       exclude_comments: bool = False) -> Rect:
        if self.has_geometry():
            return self._rect.copy()
        return ElementCollection.get_bound_rect(self, d, exclude_comments)

    def get_transitions(self) -> List[Element]:
        return self.find_elements_by_type(elementTransition)
