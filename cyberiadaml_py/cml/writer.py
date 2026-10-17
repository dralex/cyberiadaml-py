# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# Writing: the element tree of the binding as a core model
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
"""Writing: the element tree as a core model, written by the core writer."""
import math
from typing import Any, Dict, List, Optional

from .. import core
from . import errors
from .actions import Action
from .elements import (Choice, Comment, Element, ElementCollection, State,
                       StateMachine, SubmachineState, Transition, Vertex)
from .enums import (ElementType, actionEntry, actionExit, actionTransition,
                    commentSubjectData, commentSubjectName,
                    eventPropagationDefer, elementInitial,
                    geometryFormatNone, geometryFormatQt)
from .geometry import Point, Polyline, Rect

REGION_SUFFIX = ':'
KINDS = {
    ElementType.elementInitial: 'initial',
    ElementType.elementFinal: 'final',
    ElementType.elementChoice: 'choice',
    ElementType.elementTerminate: 'terminate',
    ElementType.elementShallowHistory: 'shallowHistory',
    ElementType.elementDeepHistory: 'deepHistory',
    ElementType.elementEntryPoint: 'entryPoint',
    ElementType.elementExitPoint: 'exitPoint',
}
PROPAGATION_WORDS = {1: 'block', 2: 'propagate', 3: 'defer'}
# the decimal places of the rounded geometry: positions finer than sizes
ROUND_SIZE = 3
ROUND_POSITION = ROUND_SIZE + 1


def _round(value: float, places: int) -> float:
    scale = 10 ** places
    return math.copysign(math.floor(abs(value) * scale + 0.5) / scale, value)


def action_text(actions: List[Action]) -> Optional[str]:
    """Return the behaviour text as the C library writes it."""
    blocks = []
    for action in actions:
        kind = action.get_type()
        if kind == actionTransition and action.is_empty_transition() and \
                not action.has_propagation():
            continue
        if kind == actionEntry:
            head = 'entry/'
        elif kind == actionExit:
            head = 'exit/'
        else:
            head = action.get_trigger()
            if action.get_guard():
                head += (' ' if head else '') + '[%s]' % action.get_guard()
            word = PROPAGATION_WORDS.get(int(action.get_propagation()))
            if word and action.get_propagation() != eventPropagationDefer:
                head += (' ' if head else '') + word
            head += '/'
            if action.get_propagation() == eventPropagationDefer:
                head += ' defer'
        if action.get_behavior():
            head += '\n' + action.get_behavior()
        blocks.append(head)
    return '\n\n'.join(blocks) if blocks else None


class _Writer:
    """One encode: the element tree as a core document."""

    def __init__(self, doc, geometry: bool, round_: bool,
                 skip_empty_behavior: bool, strict_actions: bool) -> None:
        self.doc = doc
        self.geometry = geometry
        self.round = round_
        self.skip_empty = skip_empty_behavior
        self.strict_actions = strict_actions

    def point(self, value: Point) -> Optional[core.Point]:
        if not self.geometry or not value.valid:
            return None
        if self.round:
            return core.Point(_round(value.x, ROUND_POSITION),
                              _round(value.y, ROUND_POSITION))
        return core.Point(value.x, value.y)

    def rect(self, value: Rect) -> Optional[core.Rect]:
        if not self.geometry or not value.valid:
            return None
        if self.round:
            return core.Rect(_round(value.x, ROUND_POSITION),
                             _round(value.y, ROUND_POSITION),
                             _round(value.width, ROUND_SIZE),
                             _round(value.height, ROUND_SIZE))
        return core.Rect(value.x, value.y, value.width, value.height)

    def polyline(self, value: Polyline) -> List[core.Point]:
        points = [self.point(p) for p in value]
        return [p for p in points if p is not None]

    def actions(self, state: State) -> Optional[str]:
        actions: List[Action] = []
        for action in state._actions:
            kind = action.get_type()
            if kind != actionTransition:
                if self.skip_empty and not action.get_behavior():
                    continue
                same = [a for a in actions if a.get_type() == kind]
                if same:
                    if self.strict_actions:
                        raise errors.error(
                            errors.CybMLException, 'Multiple %s actions' %
                            ('entry' if kind == actionEntry else 'exit'))
                    same[0]._behavior += '\n' + action.get_behavior()
                    continue
            actions.append(action.copy())
        return action_text(actions)

    def node(self, element: Element):
        common: Dict[str, Any] = dict(name=element._name,
                                      formal_name=element._formal_name)
        node: Any
        if isinstance(element, Comment):
            return core.Comment(
                element.get_id(), None,
                kind='informal' if element.is_human_readable() else 'formal',
                body=element.get_body(), markup=element._markup or None,
                geometry=self.rect(element._rect),
                color=element._color or None, **common)
        if isinstance(element, Choice):
            return core.Vertex(element.get_id(), None, kind='choice',
                               geometry=self.rect(element._rect),
                               color=element._color or None, **common)
        if isinstance(element, Vertex):
            return core.Vertex(element.get_id(), None,
                               kind=KINDS[element.get_type()],
                               geometry=self.point(element._point),
                               color=element._color or None, **common)
        if isinstance(element, SubmachineState):
            node = core.SubmachineState(
                element.get_id(), None, ref=element.get_submachine_reference(),
                geometry=self.rect(element._rect),
                color=element._color or None, **common)
        else:
            assert isinstance(element, State)
            node = core.State(element.get_id(), None,
                              data=self.actions(element),
                              collapsed=element.is_collapsed(),
                              geometry=self.rect(element._rect),
                              color=element._color or None, **common)
        if element._children:
            region = core.Region(element.get_id() + REGION_SUFFIX, None)
            if isinstance(element, State) and \
                    not isinstance(element, SubmachineState):
                region.geometry = self.rect(element._region_rect)
            region.children = [self.node(c) for c in element._children
                               if not isinstance(c, Transition)]
            node.regions = [region]
        return node

    def machine(self, sm: StateMachine) -> core.StateMachine:
        machine = core.StateMachine(sm.get_id(), None, name=sm._name,
                                    formal_name=sm._formal_name,
                                    geometry=self.rect(sm._rect),
                                    marker=True)
        machine.children = [self.node(c) for c in sm._children
                            if not isinstance(c, Transition)]
        for transition in sm.get_transitions():
            assert isinstance(transition, Transition)
            label = self.point(transition._label_point) or \
                self.rect(transition._label_rect)
            machine.transitions.append(core.Transition(
                transition.get_id(), None,
                source=transition.get_source_element_id(),
                target=transition.get_target_element_id(),
                data=action_text([transition._action]),
                polyline=self.polyline(transition._polyline),
                source_point=self.point(transition._sp),
                target_point=self.point(transition._tp),
                label_geometry=label, color=transition._color or None))
        for comment in sm.get_comments():
            assert isinstance(comment, Comment)
            for subject in comment.get_subjects():
                kind = subject.get_type()
                pivot = 'dName' if kind == commentSubjectName else \
                    'dData' if kind == commentSubjectData else ''
                machine.links.append(core.CommentLink(
                    subject.get_id(), None, source=comment.get_id(),
                    target=subject.get_element().get_id(), pivot=pivot,
                    chunk=subject.get_fragment() if pivot else None,
                    polyline=self.polyline(subject._polyline),
                    source_point=self.point(subject._source),
                    target_point=self.point(subject._target)))
        return machine


def build(doc, round_: bool, skip_geometry: bool, check_initial: bool,
          strict_actions: bool, skip_empty_behavior: bool) -> core.Document:
    """Return the core document of the element tree."""
    machines = doc.get_state_machines()
    if not machines:
        raise errors.error(errors.ParametersException,
                           'Empty SM document to write')
    geometry = doc._geometry_format != geometryFormatNone and \
        not skip_geometry
    if geometry and doc._geometry_format == geometryFormatQt:
        raise errors.error(errors.NotImplementedException,
                           'the Qt geometry format')
    if not geometry:
        # the library takes no other option without the geometry
        round_ = check_initial = strict_actions = skip_empty_behavior = False
    if check_initial:
        for sm in machines:
            initials = [c for c in sm._children
                        if c.get_type() == elementInitial]
            if len(initials) != 1:
                raise errors.error(errors.CybMLException, 'SM should have '
                                   'single initial pseudostate on the top '
                                   'level')
    writer = _Writer(doc, geometry, round_, skip_empty_behavior,
                     strict_actions)
    document = core.Document(None, format=core.FORMAT_STANDARD)
    meta = doc._meta
    params = [('standardVersion', meta.standard_version)] + \
        list(meta.strings)
    order = {1: 'actionFirst', 2: 'exitFirst'}.get(
        int(meta.transition_order))
    if order:
        params.append(('transitionOrder', order))
    propagation = {1: 'block', 2: 'propagate'}.get(
        int(meta.event_propagation))
    if propagation:
        params.append(('eventPropagation', propagation))
    document.meta_params = [core.Param(name, value, index)
                            for index, (name, value) in enumerate(params)]
    document.machines = [writer.machine(sm) for sm in machines]
    meta_id = doc._meta_element.get_id() if doc._meta_element else None
    for node in document.machines[0].children:
        if isinstance(node, core.Comment) and node.id == meta_id:
            document.meta_comment = node
    return document


def encode(doc, round_: bool, skip_geometry: bool, check_initial: bool,
           strict_actions: bool, skip_empty_behavior: bool) -> str:
    """Return the standard document text of the element tree."""
    document = build(doc, round_, skip_geometry, check_initial,
                     strict_actions, skip_empty_behavior)
    try:
        return core.write(document)
    except core.CGMLError as err:
        from .reader import _error
        raise _error(err.findings, '', True) from None
