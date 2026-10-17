# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# Reading: the core model as the element tree of the binding
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
"""Reading: the core model as the element tree of the binding."""
import re
from typing import Dict, List, Optional, Set, Tuple

from .. import core
from . import errors
from .actions import Action
from .document import Document, DocumentMetainformation
from .elements import (Choice, Comment, CommentSubject, ConnectionPoint,
                       Element, ElementCollection, Final, History, Initial,
                       State, StateMachine, SubmachineState, Terminate,
                       Transition)
from .enums import (DocumentGeometryFormat, EventPropagation,
                    actionEntry, actionExit,
                    commentSubjectData, commentSubjectElement,
                    commentSubjectName, docEventPropagationBlock,
                    docEventPropagationNone, docEventPropagationPropagate,
                    elementDeepHistory, elementEntryPoint, elementExitPoint,
                    elementShallowHistory, elementTransition,
                    eventPropagationBlock, eventPropagationDefer,
                    eventPropagationNone, eventPropagationPropagate,
                    geometryFormatNone, geometryFormatQt,
                    transitionLocal, transitionOrderAction,
                    transitionOrderExit, transitionOrderNone)
from .geometry import Point, Polyline, Rect

META_NAME = 'CGML_META'
META_ID = 'nMeta'
PROPAGATIONS = {'block': eventPropagationBlock,
                'propagate': eventPropagationPropagate,
                'defer': eventPropagationDefer}
KEYWORDS = {'entry': actionEntry, 'exit': actionExit}
POINT_KINDS = {'initial': Initial, 'final': Final, 'terminate': Terminate}
HISTORY_KINDS = {'shallowHistory': elementShallowHistory,
                 'deepHistory': elementDeepHistory}
POINT_TYPES = {'entryPoint': elementEntryPoint, 'exitPoint': elementExitPoint}
EMPTY_ACTION = 'Internal load error: Parameters Exception: Empty ' \
    'transition action is not allowed'
YED_MARKS = ('yworks', 'yfiles')
# the errors the binding refuses in its non-strict mode as well; the others
# stay findings (found by the conformance examples)
LENIENT_REFUSED = frozenset((
    'behaviour-syntax', 'chunk-required', 'data-key-attr', 'edge-endpoints',
    'event-propagation-value', 'formal-name-syntax', 'gformat-first',
    'gformat-value', 'graph-in-graph', 'key-declarations', 'link-target',
    'link-target-kind', 'markup-usage', 'meta-presence', 'meta-syntax',
    'note-value', 'standard-version',
    'pivot-value', 'points-first-region', 'region-marker-required',
    'single-initial', 'submachine-subgraph', 'tag-tree',
    'transition-endpoints', 'unique-data-keys', 'vertex-value'))
# an undeclared extension key the binding skips (key-declarations)
UNDECLARED_KEY = 'data key '
# the comment link errors the binding meets as a failed internal check
ASSERTED = frozenset(('chunk-required', 'link-target-kind'))
# the event names the binding reads: words, spaces and dots, one argument
TRIGGER = re.compile(r'\w((\w| |\.)*\w)?(\(\w+\))?\Z')
LAPKI_HINT = 'lapkiVisual'
# the Arena documents carry this key (the libcyberiadaml Arena dialect)
ARENA = re.compile(r'<data\s[^>]*key\s*=\s*["\']referenceGraphID["\']')
FORMAT_ARENA = 'Cyberiada-GraphML-Arena'


def _rstrip(text: Optional[str]) -> Optional[str]:
    return text.rstrip() if text is not None else None


def _guard(text: Optional[str]) -> str:
    # the binding keeps the guard as written: the brackets escaped
    if text is None:
        return ''
    return text if text == 'else' else \
        text.replace('[', '\\[').replace(']', '\\]')


def _behavior(block) -> str:
    return '\n'.join(block.behaviour).strip()


def _trigger(block, node: bool) -> str:
    trigger = block.trigger.strip()
    if (trigger and not TRIGGER.match(trigger)) or \
            (node and '/' not in block.verbatim):
        raise errors.error(errors.CybMLException,
                           "Bad action '%s'" % block.verbatim)
    return trigger


def _event(block, node: bool) -> Tuple[str, EventPropagation]:
    """Return the trigger and the propagation of an event block."""
    trigger = _trigger(block, node)
    if block.param:
        return trigger, PROPAGATIONS[block.param]
    # the C library also takes a keyword ending the trigger ('EV defer/')
    for word, value in PROPAGATIONS.items():
        if trigger.endswith(' ' + word):
            return trigger[:-len(word)].strip(), value
    return trigger, EventPropagation(eventPropagationNone)


def _legacy(finding) -> bool:
    # repairs the binding makes without calling the document Lapki
    return finding.rule in ('lapki-d8a', 'lapki-d7f') or \
        (finding.rule == 'lapki-d1' and finding.message.startswith(
            ('metadata parameter', 'metadata without a standardVersion')))


def _label(document) -> str:
    if document.label != core.FORMAT_LAPKI or \
            any(p.name == LAPKI_HINT for p in document.meta_params):
        return document.label
    repairs = [f for f in document.findings
               if f.layer == 0 and not _legacy(f)]
    return core.FORMAT_LAPKI if repairs else core.FORMAT_STANDARD


def _point(shape) -> Point:
    if isinstance(shape, (core.Point, core.Rect)):
        return Point(shape.x, shape.y)
    return Point()


def _rect(shape) -> Rect:
    if isinstance(shape, core.Rect):
        return Rect(shape.x, shape.y, shape.width, shape.height)
    if isinstance(shape, core.Point):
        return Rect(shape.x, shape.y, 0, 0)
    return Rect()


def _has_geometry(document) -> bool:
    for machine in document.machines:
        if machine.geometry is not None:
            return True
        for node in core.model.iter_machine_nodes(machine):
            if node.geometry is not None or any(
                    r.geometry is not None
                    for r in getattr(node, 'regions', [])):
                return True
        for edge in machine.transitions + machine.links:
            if edge.polyline or edge.source_point or edge.target_point or \
                    getattr(edge, 'label_geometry', None) is not None:
                return True
    return False


def _error(findings: list, text: str, strict: bool) -> errors.Exception:
    if 'Cyberiada-GraphML' not in text and \
            any(mark in text for mark in YED_MARKS):
        return errors.error(errors.NotImplementedException,
                            'the yEd formats')
    findings = [f for f in findings if f.severity == core.ERROR] or findings
    if not findings:
        return errors.error(errors.CybMLException, 'the document is wrong')
    first = findings[0]
    if first.layer == 1 or first.rule == 'root-graphml':
        return errors.error(errors.XMLException, first.message)
    # the binding checks the metainformation first; a missing CGML_META
    # next to other errors is their consequence
    meta = [f for f in findings if (f.req or '').startswith('CGML-6.9') and
            (f.rule != 'meta-presence' or len(findings) == 1) or
            f.rule == 'document-model']
    if meta:
        return errors.error(errors.MetainfoException, meta[0].message)
    if not strict and first.rule in ASSERTED:
        return errors.error(errors.AssertException, first.message)
    return errors.error(errors.CybMLException, first.message)


class _Reader:
    """One decode: the core document into a Document."""

    def __init__(self, doc: Document, gf: DocumentGeometryFormat,
                 skip_empty_actions: bool, strict: bool) -> None:
        self.doc = doc
        self.geometry = gf != geometryFormatNone
        self.skip_empty_actions = skip_empty_actions
        self.strict = strict
        self.elements: Dict[str, Element] = {}
        self.initials: Set[Optional[str]] = set()
        self.regions: Set[int] = set()   # states whose children had a region
        self.original: Dict[str, str] = {}
        self.edges: Set[str] = set()

    def ident(self, value: Optional[str]) -> str:
        # the ids per machine as written: the dialect renames are undone
        return self.original.get(value or '', value or '')

    def edge_ident(self, value: Optional[str]) -> str:
        # a renamed duplicate stays renamed if its id is taken in the machine
        ident = self.ident(value)
        if ident in self.edges:
            ident = value or ''
        self.edges.add(ident)
        return ident

    def meta(self, document, skip_meta_format: bool) -> None:
        meta = self.doc._meta = DocumentMetainformation()
        if skip_meta_format:
            return
        meta.transition_order = transitionOrderNone
        meta.event_propagation = docEventPropagationNone
        for param in document.meta_params:
            value = param.value.strip()
            if param.name == 'standardVersion':
                meta.standard_version = value
            elif param.name == 'transitionOrder':
                meta.transition_order = {
                    'actionFirst': transitionOrderAction,
                    'transitionFirst': transitionOrderAction,
                    'exitFirst': transitionOrderExit}.get(
                        value, transitionOrderNone)
            elif param.name == 'eventPropagation':
                meta.event_propagation = {
                    'block': docEventPropagationBlock,
                    'propagate': docEventPropagationPropagate}.get(
                        value, docEventPropagationNone)
            else:
                meta.strings.append((param.name, value))
        self.doc._name = meta.get_string('name')

    def machine(self, document, machine) -> StateMachine:
        name = _rstrip(machine.name) or machine.id or ''
        sm = StateMachine(self.doc, machine.id or '', name,
                          _rect(machine.geometry) if self.geometry else None)
        self.doc._attach(sm)
        self.original = dict(document.original_ids)
        self.elements = {}
        self.edges = set()
        self.initials = {self.ident(n.id)
                         for n in core.model.iter_machine_nodes(machine)
                         if isinstance(n, core.Vertex) and
                         n.kind == 'initial'}
        for child in machine.children:
            self.node(document, child, sm)
        for transition in machine.transitions:
            self.transition(transition, sm)
        for link in machine.links:
            self.link(link)
        return sm

    def node(self, document, node, parent: ElementCollection) -> None:
        element: Element
        if isinstance(node, core.Comment):
            element = self.comment(document, node, parent)
        elif isinstance(node, core.Vertex):
            element = self.vertex(node, parent)
        elif isinstance(node, core.SubmachineState):
            element = SubmachineState(
                parent, self.ident(node.id), _rstrip(node.name) or '',
                node.ref or '',
                _rect(node.geometry) if self.geometry else None,
                node.color or '')
        else:
            element = self.state(node, parent)
        element._formal_name = _rstrip(node.formal_name)
        parent._attach(element)
        self.elements[element.get_id()] = element
        regions = getattr(node, 'regions', [])
        if isinstance(node, core.State) and len(regions) > 1:
            raise errors.error(
                errors.CybMLException, 'More than one region node for '
                'node %s are not supported' % node.id)
        if isinstance(node, core.State) and regions:
            self.regions.add(id(element))
        for region in regions:
            for child in region.children:
                self.node(document, child, element)  # type: ignore[arg-type]

    def comment(self, document, node, parent) -> Comment:
        body = node.body or ''
        if node is document.meta_comment:
            body = self.doc._meta.encode()
        name = _rstrip(node.name)
        comment = Comment(parent, self.ident(node.id), body,
                          human_readable=node.kind != 'formal',
                          markup=node.markup or '',
                          rect=_rect(node.geometry) if self.geometry
                          else None, color=node.color or '')
        comment._name = name
        if node is document.meta_comment:
            self.doc._meta_element = comment
        return comment

    def vertex(self, node, parent) -> Element:
        kind = (node.kind or '').strip()
        ident = self.ident(node.id)
        point = _point(node.geometry) if self.geometry else None
        name = _rstrip(node.name)
        element: Element
        if kind in POINT_KINDS:
            element = POINT_KINDS[kind](parent, ident, point=point)
        elif kind == 'choice':
            element = Choice(parent, ident,
                             rect=_rect(node.geometry) if self.geometry
                             else None, color=node.color or '')
        elif kind in HISTORY_KINDS:
            element = History(parent, HISTORY_KINDS[kind], ident,
                              point=point, color=node.color or '')
        elif kind in POINT_TYPES:
            element = ConnectionPoint(parent, POINT_TYPES[kind],
                                      ident, point=point,
                                      color=node.color or '')
        else:
            raise errors.error(errors.CybMLException,
                               'Unsupported node type %s' % kind)
        element._name = name
        if node.color and kind in POINT_KINDS:
            element._color = node.color  # type: ignore[attr-defined]
        return element

    def state(self, node, parent) -> State:
        state = State(parent, self.ident(node.id), _rstrip(node.name) or '',
                      _rect(node.geometry) if self.geometry else None,
                      _rect(node.regions[0].geometry)
                      if self.geometry and node.regions else None,
                      node.color or '')
        state._name = _rstrip(node.name)
        state._collapsed = bool(node.collapsed)
        state._actions = self.state_actions(node)
        return state

    def state_actions(self, node) -> List[Action]:
        actions: List[Action] = []
        for block in node.blocks:
            trigger = block.trigger.strip()
            kind = block.kind if block.kind != 'event' else trigger
            if kind == 'do':
                raise errors.error(errors.CybMLException,
                                   'Unsupported action type 8')
            if kind in KEYWORDS:
                if block.guard is not None:
                    raise errors.error(
                        errors.CybMLException, 'Guards are not allowed '
                        'for entry/exit activities')
                behavior = _behavior(block)
                same = [a for a in actions if a.get_type() == KEYWORDS[kind]]
                if same and not self.strict:
                    same[0]._behavior += '\n' + behavior
                    continue
                actions.append(Action(KEYWORDS[kind], behavior))
                continue
            trigger, propagation = _event(block, True)
            actions.append(Action(trigger, _guard(block.guard),
                                  _behavior(block), propagation))
        if self.skip_empty_actions:
            actions = [a for a in actions
                       if a.get_behavior() or a.get_guard()]
        if any(a.is_empty_transition() for a in actions):
            raise errors.error(errors.AssertException, EMPTY_ACTION)
        return actions

    def transition(self, edge, sm: StateMachine) -> None:
        geometry = self.geometry
        label = edge.label_geometry if geometry else None
        source, target = self.ident(edge.source), self.ident(edge.target)
        transition = Transition(
            sm, transitionLocal,
            self.edge_ident(edge.id or '%s-%s' % (source, target)),
            source, target, self.edge_action(edge),
            Polyline([Point(p.x, p.y) for p in edge.polyline])
            if geometry else None,
            _point(edge.source_point) if geometry else None,
            _point(edge.target_point) if geometry else None,
            _point(label) if isinstance(label, core.Point) else None,
            _rect(label) if isinstance(label, core.Rect) else None,
            edge.color or '')
        sm._attach(transition)
        self.elements[transition.get_id()] = transition

    def edge_action(self, edge) -> Action:
        if not edge.blocks:
            return Action()
        block = edge.blocks[0]
        data = edge.data or ''
        # a lone trigger on an initial transition is its behaviour (Lapki)
        if not self.strict and self.ident(edge.source) in self.initials and \
                block.kind == 'event' and block.guard is None and \
                not block.param and not block.behaviour and \
                block.trigger and '/' not in data:
            return Action('', '', data.strip())
        if block.kind != 'event':
            raise errors.error(errors.CybMLException, 'Transitions cannot '
                               'contain entry/exit activities')
        trigger, propagation = _event(block, False)
        return Action(trigger, _guard(block.guard), _behavior(block),
                      propagation)

    def link(self, edge) -> None:
        comment = self.elements.get(self.ident(edge.source))
        target = self.elements.get(self.ident(edge.target))
        if not isinstance(comment, Comment) or target is None:
            raise errors.error(errors.AssertException,
                               'bad comment link %s' % edge.id)
        pivot = (edge.pivot or '').strip()
        kind = {'dName': commentSubjectName,
                'dData': commentSubjectData}.get(pivot, commentSubjectElement)
        geometry = {}
        if self.geometry:
            geometry = dict(source=_point(edge.source_point),
                            target=_point(edge.target_point),
                            polyline=Polyline([Point(p.x, p.y)
                                               for p in edge.polyline]))
        ident = self.edge_ident(edge.id)
        if kind == commentSubjectElement:
            subject = CommentSubject(ident, target, **geometry)
        else:
            subject = CommentSubject(ident, target, kind, edge.chunk or '',
                                     **geometry)
        comment._subjects.append(subject)

    def simplify_ids(self) -> None:
        """Renumber as the binding does: g0, n<k>, <parent>::n<k>."""
        renamed: Dict[str, str] = {}
        counter = 0
        for sm in self.doc.get_state_machines():
            sm._id = 'g0'
            self._renumber(sm, '', renamed)
            taken: Set[str] = set()
            for transition in sm.get_transitions():
                assert isinstance(transition, Transition)
                source = renamed.get(transition._source, transition._source)
                target = renamed.get(transition._target, transition._target)
                transition._source, transition._target = source, target
                ident = '%s-%s' % (source, target)
                if ident in taken:
                    ident = '%s#%d' % (ident, counter)
                    counter += 1
                taken.add(ident)
                transition._id = ident

    def _renumber(self, collection, prefix: str, renamed: Dict[str, str]):
        index = 0
        for child in collection.get_children():
            if child.get_type() == elementTransition:
                continue
            new = '%sn%d' % (prefix, index)
            index += 1
            renamed[child._id] = new
            child._id = new
            if isinstance(child, ElementCollection):
                inner = new + '::'
                if id(child) in self.regions:
                    inner += 'n0::'
                self._renumber(child, inner, renamed)


def read(doc: Document, text: str, gf: DocumentGeometryFormat,
         skip_empty_actions: bool, simplify_ids: bool,
         skip_meta_format: bool, strict: bool) -> str:
    """Fill doc from the document text; return the format string."""
    try:
        document = core.read(text, strict=strict)
    except core.CGMLError as err:
        raise _error(err.findings, text, strict) from None
    refused = [f for f in document.findings if f.severity == core.ERROR and
               f.rule in LENIENT_REFUSED and not (
                   f.rule == 'key-declarations' and
                   f.message.startswith(UNDECLARED_KEY))]
    if refused:
        raise _error(refused, text, strict)
    arena = ARENA.search(text) is not None
    if gf != geometryFormatNone and _has_geometry(document) and (
            arena or gf == geometryFormatQt):
        raise errors.error(errors.NotImplementedException,
                           'the Arena geometry' if arena
                           else 'the Qt geometry format')
    if document.meta_comment is None and not skip_meta_format:
        raise errors.error(errors.MetainfoException,
                           'No CGML_META formal comment in the document')
    reader = _Reader(doc, gf, skip_empty_actions, strict)
    reader.meta(document, skip_meta_format)
    for machine in document.machines:
        reader.machine(document, machine)
    if skip_meta_format:
        machines = doc.get_state_machines()
        meta = doc._meta_element
        if meta is None and machines:
            meta = Comment(machines[0], META_ID, '', human_readable=False)
            meta._name = META_NAME
            machines[0]._children.insert(0, meta)
            doc._meta_element = meta
        if meta is not None:
            meta._body = doc._meta.encode()
    if simplify_ids:
        reader.simplify_ids()
    if reader.geometry and _has_geometry(document):
        doc._geometry_format = DocumentGeometryFormat(gf)
    if arena:
        return FORMAT_ARENA
    return core.FORMAT_STANDARD if skip_meta_format else _label(document)
