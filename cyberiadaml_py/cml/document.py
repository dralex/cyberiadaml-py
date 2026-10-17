# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The documents of the CyberiadaML interface
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
"""The metainformation, Document and LocalDocument."""
import copy as copying
import pathlib
from typing import Any, List, Optional, Tuple

from .. import core
from . import errors
from .actions import Action
from .elements import (Choice, Comment, CommentSubject, ConnectionPoint,
                       Element, ElementCollection, Final, History, Initial,
                       State, StateMachine, SubmachineState, Terminate,
                       Transition)
from .enums import (DocumentEventPropagation, DocumentFormat,
                    DocumentGeometryDeclaration, DocumentGeometryFormat,
                    DocumentTransitionOrder, docEventPropagationBlock,
                    docEventPropagationNone, docEventPropagationPropagate,
                    ElementType, TransitionType, actionTransition,
                    commentSubjectData, commentSubjectName,
                    elementChoice, elementComment, elementDeepHistory,
                    elementEntryPoint, elementExitPoint, elementFinal,
                    elementFormalComment, elementInitial, elementRoot,
                    elementShallowHistory, elementSM, elementTerminate,
                    elementTransition, formatCyberiada10, formatDetect,
                    formatLapki, formatLegacyYED, formatLegacyYEDBerloga16,
                    formatLegacyYEDOstranna, geometryDeclarationAbsent,
                    geometryFormatNone, geometryFormatQt,
                    transitionOrderAction, transitionOrderExit,
                    transitionOrderNone)
from .geometry import Point, Polyline, Rect

GEOMETRY_WORDS = {1: 'none', 2: 'short', 3: 'full'}
BAD_SOURCES = (elementRoot, elementSM, elementComment, elementFormalComment,
               elementFinal, elementTerminate, elementTransition)
BAD_TARGETS = (elementRoot, elementSM, elementComment, elementFormalComment,
               elementInitial, elementTransition)
HISTORY_NAMES = {elementShallowHistory: 'shallow', elementDeepHistory: 'deep'}


def _strings(args: tuple) -> int:
    """Return how many arguments in front are strings (the overload)."""
    count = 0
    while count < len(args) and isinstance(args[count], str):
        count += 1
    return count


def _option(rest: tuple, kwargs: dict, index: int, name: str,
            default: Any = None) -> Any:
    return rest[index] if index < len(rest) else kwargs.get(name, default)


def _fail(message: str) -> errors.Exception:
    return errors.error(errors.ParametersException, message)


GEOMETRY_NAMES = {
    'none': DocumentGeometryDeclaration.geometryDeclarationNone,
    'short': DocumentGeometryDeclaration.geometryDeclarationShort,
    'full': DocumentGeometryDeclaration.geometryDeclarationFull}
GEOMETRY_FORMAT_NAMES = {0: 'none', 1: 'yed', 2: 'cyb', 3: 'qt'}
FILE_FORMAT_NAMES = {0: 'cyberiada', 1: 'yed', 2: 'yed-ostranna',
                     3: 'yed-berloga', 4: 'lapki'}


class DocumentMetainformation:
    """The metainformation of a document (the CGML_META parameters)."""

    def __init__(self) -> None:
        self.standard_version = '1.0'
        self.transition_order = DocumentTransitionOrder(
            transitionOrderAction)
        self.event_propagation = DocumentEventPropagation(
            docEventPropagationBlock)
        self.strings: List[Tuple[str, str]] = []

    def get_string(self, name: str) -> str:
        for key, value in self.strings:
            if key == name:
                return value
        return ''

    def set_string(self, name: str, value: str) -> None:
        for index, (key, _) in enumerate(self.strings):
            if key == name:
                self.strings[index] = (name, value)
                return
        self.strings.append((name, value))

    def remove_string(self, name: str) -> None:
        self.strings = [item for item in self.strings if item[0] != name]

    def set_geometry(self, declaration: DocumentGeometryDeclaration) -> None:
        word = GEOMETRY_WORDS.get(int(declaration))
        if word is None:
            self.remove_string('geometry')
        else:
            self.set_string('geometry', word)

    def get_geometry(self) -> DocumentGeometryDeclaration:
        value = self.get_string('geometry')
        if not value:
            return DocumentGeometryDeclaration(geometryDeclarationAbsent)
        return GEOMETRY_NAMES.get(value, DocumentGeometryDeclaration(
            geometryDeclarationAbsent))

    def encode(self) -> str:
        """Return the CGML_META body of the metainformation."""
        params = ['standardVersion/ %s' % self.standard_version]
        params += ['%s/ %s' % item for item in self.strings]
        if self.transition_order == transitionOrderAction:
            params.append('transitionOrder/ actionFirst')
        elif self.transition_order == transitionOrderExit:
            params.append('transitionOrder/ exitFirst')
        if self.event_propagation == docEventPropagationBlock:
            params.append('eventPropagation/ block')
        elif self.event_propagation == docEventPropagationPropagate:
            params.append('eventPropagation/ propagate')
        return '\n\n'.join(params)

    def dump(self) -> str:
        """Return the meta part of the document dump."""
        params = []
        if self.standard_version:
            params.append("standard version: '%s'" % self.standard_version)
        params += ["%s: '%s'" % item for item in self.strings]
        if self.transition_order != transitionOrderNone:
            params.append('transition order: %s' % (
                'exit first' if self.transition_order == transitionOrderExit
                else 'action first'))
        if self.event_propagation != docEventPropagationNone:
            params.append('event propagation: %s' % (
                'propagate events' if self.event_propagation ==
                docEventPropagationPropagate else 'block events'))
        return ', '.join(params)


class Document(ElementCollection):
    """A document: Document(format=geometryFormatNone) or Document(d)."""

    def __init__(self, format: Any =
                 DocumentGeometryFormat(geometryFormatNone)) -> None:
        super().__init__(None, elementRoot, '', '')
        if isinstance(format, Document):
            self._copy_from(format)
            return
        self._init(format)

    def _copy_from(self, source: 'Document') -> None:
        clone = copying.deepcopy(source)
        for name in ('_children', '_name', '_meta', '_geometry_format',
                     '_meta_element'):
            setattr(self, name, getattr(clone, name))
        for child in self._children:
            child._parent = self

    def _init(self, format: DocumentGeometryFormat) -> None:
        self._children = []
        self._name = ''
        self._meta = DocumentMetainformation()
        self._geometry_format = DocumentGeometryFormat(format)
        self._meta_element: Optional[Comment] = None

    def decode(self, buffer, f: DocumentFormat =
               DocumentFormat(formatDetect),
               gf: DocumentGeometryFormat =
               DocumentGeometryFormat(geometryFormatQt),
               reconstruct: bool = False, reconstruct_sm: bool = False,
               skip_empty_actions: bool = False, simplify_ids: bool = False,
               skip_meta_format: bool = False,
               strict: bool = False) -> Tuple[DocumentFormat, str]:
        from . import reader
        if not all(isinstance(v, int) for v in (f, gf)):
            raise TypeError('decode(): incompatible function arguments')
        if isinstance(buffer, bytes):
            buffer = buffer.decode('utf-8')
        if not buffer:
            raise errors.error(errors.ParametersException,
                               'Empty buffer to decode')
        if reconstruct or reconstruct_sm:
            raise errors.error(errors.NotImplementedException,
                               'the geometry reconstruction')
        if f not in (formatDetect, formatCyberiada10, formatLapki):
            raise errors.error(errors.NotImplementedException,
                               'the yEd formats')
        self._init(geometryFormatNone)
        label = reader.read(self, buffer, gf, skip_empty_actions,
                            simplify_ids, skip_meta_format, strict)
        return DocumentFormat(formatCyberiada10), label

    def get_meta(self) -> DocumentMetainformation:
        return self._meta

    def reset(self, format: DocumentGeometryFormat =
              DocumentGeometryFormat(geometryFormatNone)) -> None:
        self._init(format)

    def set_name(self, name: str) -> None:
        self._name = name
        self._meta.set_string('name', name)
        self._update_meta_element()

    def set_geometry(self, format: DocumentGeometryFormat) -> None:
        self._geometry_format = DocumentGeometryFormat(format)

    def clean_geometry(self) -> None:
        super().clean_geometry()
        self._geometry_format = DocumentGeometryFormat(geometryFormatNone)

    def convert_geometry(self, gf: DocumentGeometryFormat) -> None:
        if gf == self._geometry_format:
            return
        if gf == geometryFormatNone:
            self.clean_geometry()
            return
        raise errors.error(errors.NotImplementedException,
                           'the geometry conversion')

    def check_geometry(self) -> bool:
        raise errors.error(errors.NotImplementedException,
                           'the geometry check')

    def reconstruct_geometry(self, reconstruct_sm: bool = False) -> None:
        raise errors.error(errors.NotImplementedException,
                           'the geometry reconstruction')

    def update_geometry(self, *args) -> None:  # type: ignore[override]
        raise errors.error(errors.NotImplementedException,
                           'the geometry update')

    def get_bound_rect(self, *args) -> Rect:
        raise errors.error(errors.NotImplementedException,
                           'the bounding rect')

    def update_metainfo_from_comment(self, body: str) -> bool:
        # a stub in the C++ library as well
        return False

    def _update_meta_element(self) -> None:
        """Write the metainformation into the CGML_META comment (C++)."""
        machines = self.get_state_machines()
        if not machines:
            return
        if self._meta_element is None:
            first = machines[0].first_element() \
                if machines[0].has_children() else None
            if not isinstance(first, Comment) or \
                    first.get_type() != elementFormalComment or \
                    not first.has_name() or first.get_name() != 'CGML_META':
                return
            self._meta_element = first
        self._meta_element._body = self._meta.encode()

    def encode(self, f: DocumentFormat = DocumentFormat(formatCyberiada10),
               round: bool = False, skip_geometry: bool = False,
               check_initial: bool = False, strict_actions: bool = False,
               skip_empty_behavior: bool = False) -> str:
        from . import writer
        if not isinstance(f, int):
            raise TypeError('encode(): incompatible function arguments')
        if f == formatDetect:
            raise _fail('Bad save format %d' % int(f))
        if f in (formatLegacyYED, formatLegacyYEDOstranna,
                 formatLegacyYEDBerloga16):
            if len(self._children) != 1:
                raise _fail('Legacy Berloga-YED format supports single-SM '
                            'documents only')
            if skip_geometry or self._geometry_format == geometryFormatNone:
                raise _fail('Legacy Berloga-YED format requires the geometry')
        if f != formatCyberiada10:
            raise errors.error(errors.NotImplementedException,
                               'writing the format %s' % f)
        return writer.encode(self, round, skip_geometry, check_initial,
                             strict_actions, skip_empty_behavior)

    # the factories

    def _taken(self, id_: str) -> bool:
        return self.find_element_by_id(id_) is not None

    def _check_id(self, id_: str) -> str:
        if self._taken(id_):
            raise _fail('New element id %s is not unique' % id_)
        return id_

    def _node_id(self, parent: Element) -> str:
        prefix = 'n' if parent is self or parent.get_type() == elementSM \
            else parent.get_id() + '::n'
        index = 0
        while self._taken('%s%d' % (prefix, index)):
            index += 1
        return '%s%d' % (prefix, index)

    def _geometry(self, *values) -> None:
        # the geometry given to a factory makes the document a Qt one
        if self._geometry_format == geometryFormatNone and any(
                getattr(v, 'valid', False) or (
                    isinstance(v, Polyline) and len(v)) for v in values):
            self._geometry_format = DocumentGeometryFormat(geometryFormatQt)

    def _container(self, parent: Optional[Element]) -> ElementCollection:
        if parent is None:
            raise _fail('No parent element')
        if not isinstance(parent, ElementCollection):
            raise _fail('Bad parent element')
        return parent

    def _named(self, args: tuple, kwargs: dict, names: int):
        """Split the id and the name off a vertex factory overload."""
        count = min(_strings(args), names)
        id_ = name = None
        if count == 2:
            id_, name = args[0], args[1]
        elif count == 1:
            name = args[0]
        else:
            id_, name = kwargs.get('id'), kwargs.get('name')
            if name is None:
                # the binding's (id, point) overload is the name one
                id_, name = None, id_
        if name is not None and not name:
            raise _fail('Empty string parameter')
        return id_, name, args[count:]

    def new_state_machine(self, *args, **kwargs) -> StateMachine:
        count = _strings(args)
        if count >= 2 or 'id' in kwargs:
            id_ = self._check_id(args[0] if count >= 2 else kwargs['id'])
            name = args[1] if count >= 2 else kwargs.get('sm_name', '')
        else:
            index = len(self.get_state_machines())
            while self._taken('G%d' % index):
                index += 1
            id_ = 'G%d' % index
            name = args[0] if count else kwargs.get('sm_name', '')
        rect = _option(args[min(count, 2):], kwargs, 0, 'rect')
        machine = StateMachine(self, id_, name, rect)
        self._attach(machine)
        self._geometry(rect)
        self._update_meta_element()
        return machine

    def new_state(self, parent, *args, **kwargs) -> State:
        parent = self._container(parent)
        count = min(_strings(args), 2)
        if count == 2:
            id_, name = self._check_id(args[0]), args[1]
        else:
            name = args[0] if count else kwargs.get('name', '')
            id_ = self._node_id(parent)
        if not name:
            raise _fail('Empty string parameter')
        rest = args[count:]
        action = _option(rest, kwargs, 0, 'action')
        rect = _option(rest, kwargs, 1, 'rect')
        region = _option(rest, kwargs, 2, 'region_rect')
        state = State(parent, id_, name, rect, region,
                      _option(rest, kwargs, 3, 'color', ''))
        if action is not None and not action.is_empty_transition():
            state.add_action(action)
        parent._attach(state)
        self._geometry(rect, region)
        return state

    def new_submachine_state(self, parent, *args,
                             **kwargs) -> SubmachineState:
        parent = self._container(parent)
        count = min(_strings(args), 3)
        if count == 3:
            id_ = self._check_id(args[0])
            reference, name = args[1], args[2]
        else:
            id_ = self._node_id(parent)
            reference = args[0] if count else kwargs.get('reference', '')
            name = args[1] if count == 2 else kwargs.get('name', '')
        if not reference:
            raise _fail('Empty string parameter')
        rest = args[count:]
        rect = _option(rest, kwargs, 0, 'rect')
        state = SubmachineState(parent, id_, name, reference, rect,
                                _option(rest, kwargs, 1, 'color', ''))
        parent._attach(state)
        self._geometry(rect)
        return state

    def _vertex(self, parent, args: tuple, kwargs: dict, build) -> Any:
        parent = self._container(parent)
        id_, name, rest = self._named(args, kwargs, 2)
        id_ = self._check_id(id_) if id_ is not None else \
            self._node_id(parent)
        point = _option(rest, kwargs, 0, 'point')
        color = _option(rest, kwargs, 1, 'color', '')
        vertex = build(parent, id_, point, color)
        if name is not None:
            vertex._name = name
        parent._attach(vertex)
        self._geometry(point)
        return vertex

    def new_initial(self, parent, *args, **kwargs) -> Initial:
        if parent is not None and isinstance(parent, ElementCollection) \
                and parent.has_initial():
            raise _fail('Parent already has initial element')
        return self._vertex(parent, args, kwargs, lambda p, i, pt, c:
                            Initial(p, i, point=pt, color=c))

    def new_final(self, parent, *args, **kwargs) -> Final:
        return self._vertex(parent, args, kwargs, lambda p, i, pt, c:
                            Final(p, i, point=pt, color=c))

    def new_terminate(self, parent, *args, **kwargs) -> Terminate:
        return self._vertex(parent, args, kwargs, lambda p, i, pt, c:
                            Terminate(p, i, point=pt, color=c))

    def _history(self, kind, parent, args, kwargs) -> History:
        if isinstance(parent, ElementCollection) and any(
                c.get_type() == kind for c in parent.get_children()):
            raise _fail('Parent already has a %s history element' %
                        HISTORY_NAMES[kind])
        return self._vertex(parent, args, kwargs, lambda p, i, pt, c:
                            History(p, kind, i, point=pt, color=c))

    def new_shallow_history(self, parent, *args, **kwargs) -> History:
        return self._history(elementShallowHistory, parent, args, kwargs)

    def new_deep_history(self, parent, *args, **kwargs) -> History:
        return self._history(elementDeepHistory, parent, args, kwargs)

    def new_entry(self, parent, *args, **kwargs) -> ConnectionPoint:
        return self._vertex(parent, args, kwargs, lambda p, i, pt, c:
                            ConnectionPoint(p, elementEntryPoint, i,
                                            point=pt, color=c))

    def new_exit(self, parent, *args, **kwargs) -> ConnectionPoint:
        return self._vertex(parent, args, kwargs, lambda p, i, pt, c:
                            ConnectionPoint(p, elementExitPoint, i,
                                            point=pt, color=c))

    def new_choice(self, parent, *args, **kwargs) -> Choice:
        parent = self._container(parent)
        id_, name, rest = self._named(args, kwargs, 2)
        id_ = self._check_id(id_) if id_ is not None else \
            self._node_id(parent)
        rect = _option(rest, kwargs, 0, 'rect')
        choice = Choice(parent, id_, rect=rect,
                        color=_option(rest, kwargs, 1, 'color', ''))
        if name is not None:
            choice._name = name
        parent._attach(choice)
        self._geometry(rect)
        return choice

    def _comment(self, parent, args, kwargs, human: bool) -> Comment:
        parent = self._container(parent)
        count = min(_strings(args), 3)
        id_ = name = None
        if count == 3:
            id_, name, body = self._check_id(args[0]), args[1], args[2]
        elif count == 2:
            name, body = args[0], args[1]
            if not name:
                raise _fail('Empty string parameter')
        else:
            body = args[0] if count else kwargs.get('body', '')
        rest = args[count:]
        rect = _option(rest, kwargs, 0, 'rect')
        comment = Comment(parent, id_ or self._node_id(parent), body,
                          human_readable=human,
                          markup=_option(rest, kwargs, 2, 'markup', ''),
                          rect=rect,
                          color=_option(rest, kwargs, 1, 'color', ''))
        comment._name = name
        parent._attach(comment)
        self._geometry(rect)
        return comment

    def new_comment(self, parent, *args, **kwargs) -> Comment:
        return self._comment(parent, args, kwargs, True)

    def new_formal_comment(self, parent, *args, **kwargs) -> Comment:
        return self._comment(parent, args, kwargs, False)

    def new_transition(self, parent, ttype: TransitionType, *args,
                       **kwargs) -> Transition:
        id_ = None
        if args and isinstance(args[0], str):
            id_, args = args[0], args[1:]
        elif 'id' in kwargs:
            id_ = kwargs['id']
        source: Any = args[0] if args else kwargs.get('source')
        target: Any = args[1] if len(args) > 1 else kwargs.get('target')
        rest = args[2:]
        action = _option(rest, kwargs, 0, 'action') or Action()
        if parent is None:
            raise _fail('No parent element')
        for element, bad, what in ((source, BAD_SOURCES, 'source'),
                                   (target, BAD_TARGETS, 'target')):
            if element is None:
                raise _fail('Empty element')
            if element.get_type() in bad:
                raise _fail('Bad %s for transition' % what)
        if target.get_type() == elementChoice and any(
                t.get_target_element_id() == target.get_id()
                for t in self.find_elements_by_type(elementTransition)
                if isinstance(t, Transition)):
            raise _fail('Choice pseudostate may have only one incoming '
                        'transition')
        if id_ is not None:
            self._check_id(id_)
        if action.get_type() != actionTransition:
            raise _fail('Transitions cannot contain entry/exit activities')
        if id_ is None:
            base = id_ = '%s-%s' % (source.get_id(), target.get_id())
            index = 0
            while self._taken(id_):
                id_ = '%s#%d' % (base, index)
                index += 1
        geometry = {n: _option(rest, kwargs, i, n) for i, n in enumerate(
            ('action', 'polyline', 'sp', 'tp', 'label_point', 'label_rect'))
            if i}
        transition = Transition(parent, ttype, id_, source.get_id(),
                                target.get_id(), action,
                                color=_option(rest, kwargs, 6, 'color', ''),
                                **geometry)
        parent._attach(transition)
        self._geometry(*geometry.values())
        return transition

    def _subject(self, comment: Comment, element, kind, fragment,
                 args: tuple, kwargs: dict) -> CommentSubject:
        if element is None:
            raise _fail('Empty element')
        if element.get_type() in (elementRoot, elementSM):
            raise _fail('Bad element to comment')
        if fragment is not None and not fragment:
            raise _fail('Empty string parameter')
        taken = {s.get_id() for s in comment.get_subjects()}
        if args and isinstance(args[0], str):
            id_, args = args[0], args[1:]
        else:
            base = id_ = '%s-%s' % (comment.get_id(), element.get_id())
            index = 0
            while id_ in taken:
                id_ = '%s#%d' % (base, index)
                index += 1
        geometry = {name: _option(args, kwargs, i, name) for i, name in
                    enumerate(('source', 'target', 'polyline'))}
        geometry = {k: v for k, v in geometry.items() if v is not None}
        if kind is None:
            subject = CommentSubject(id_, element, **geometry)
        else:
            subject = CommentSubject(id_, element, kind, fragment,
                                     **geometry)
        comment._subjects.append(subject)
        self._geometry(*geometry.values())
        return copying.copy(subject)

    def add_comment_to_element(self, comment, element, *args,
                               **kwargs) -> CommentSubject:
        return self._subject(comment, element, None, None, args, kwargs)

    def add_comment_to_element_name(self, comment, element, fragment, *args,
                                    **kwargs) -> CommentSubject:
        return self._subject(comment, element, commentSubjectName, fragment,
                             args, kwargs)

    def add_comment_to_element_body(self, comment, element, fragment, *args,
                                    **kwargs) -> CommentSubject:
        return self._subject(comment, element, commentSubjectData, fragment,
                             args, kwargs)

    meta = get_meta

    def get_meta_element(self) -> Optional[Comment]:
        return self._meta_element

    def get_state_machines(self) -> List[StateMachine]:
        return [c for c in self._children if isinstance(c, StateMachine)]

    def get_parent_sm(self, element: Element) -> Optional[StateMachine]:
        while element is not None:
            if element.get_type() == elementSM:
                return element  # type: ignore[return-value]
            if element.get_type() == elementRoot:
                return None
            element = element.get_parent()  # type: ignore[assignment]
        return None

    def get_geometry_format(self) -> DocumentGeometryFormat:
        return self._geometry_format

    def has_geometry(self) -> bool:
        return self._geometry_format != geometryFormatNone

    def _dump(self) -> str:
        text = self._prefix() + ', geometry format: %s' % \
            GEOMETRY_FORMAT_NAMES[int(self._geometry_format)]
        text += ', meta: {%s}' % self._meta.dump()
        return text + self._collection() + '}'

    def __repr__(self) -> str:
        return self._dump()


class LocalDocument(Document):
    """A document with its file.

    LocalDocument(), LocalDocument(d, path[, f]) or LocalDocument(ld).
    """

    def __init__(self, *args) -> None:
        super().__init__()
        self._file_path = ''
        self._file_format = DocumentFormat(formatCyberiada10)
        self._file_format_str = ''
        if args:
            self._copy_from(args[0])
            if isinstance(args[0], LocalDocument) and len(args) == 1:
                self._file_path = args[0]._file_path
                self._file_format = args[0]._file_format
                self._file_format_str = args[0]._file_format_str
            if len(args) > 1:
                self._file_path = args[1]
            if len(args) > 2 and args[2] != formatDetect:
                self._file_format = DocumentFormat(args[2])

    def reset(self) -> None:  # type: ignore[override]
        self._init(DocumentGeometryFormat(geometryFormatNone))
        self._file_path = self._file_format_str = ''
        self._file_format = DocumentFormat(formatCyberiada10)

    def set_file(self, path: str, f: DocumentFormat) -> None:
        self._file_path = path
        self._file_format = DocumentFormat(f)

    def save(self, round: bool = False, skip_geometry: bool = False,
             check_initial: bool = False, strict_actions: bool = False,
             skip_empty_behavior: bool = False) -> None:
        text = self.encode(self._file_format, round, skip_geometry,
                           check_initial, strict_actions,
                           skip_empty_behavior)
        try:
            pathlib.Path(self._file_path).write_text(text, encoding='utf-8')
        except OSError:
            raise errors.error(errors.FileException,
                               'Cannot open file ' + self._file_path) \
                from None

    def save_as(self, path: str, f: DocumentFormat =
                DocumentFormat(formatDetect), round: bool = False,
                skip_geometry: bool = False, check_initial: bool = False,
                strict_actions: bool = False,
                skip_empty_behavior: bool = False) -> None:
        f = self._file_format if f == formatDetect else DocumentFormat(f)
        text = self.encode(f, round, skip_geometry, check_initial,
                           strict_actions, skip_empty_behavior)
        try:
            pathlib.Path(path).write_text(text, encoding='utf-8')
        except OSError:
            raise errors.error(errors.FileException,
                               'Cannot open file ' + path) from None
        self._file_path, self._file_format = path, f

    def open(self, path: str, f: DocumentFormat =
             DocumentFormat(formatDetect),
             gf: DocumentGeometryFormat =
             DocumentGeometryFormat(geometryFormatQt),
             reconstruct: bool = False, reconstruct_sm: bool = False,
             skip_empty_actions: bool = False, simplify_ids: bool = False,
             skip_meta_format: bool = False, strict: bool = False) -> None:
        try:
            text = pathlib.Path(path).read_bytes()
        except OSError:
            raise errors.error(errors.FileException,
                               'Cannot open file ' + path) from None
        if not text:
            raise errors.error(errors.FileException,
                               'File %s is empty' % path)
        self._file_format, self._file_format_str = self.decode(
            text, f, gf, reconstruct, reconstruct_sm, skip_empty_actions,
            simplify_ids, skip_meta_format, strict)
        self._file_path = path

    def get_file_path(self) -> str:
        return self._file_path

    def get_file_format(self) -> DocumentFormat:
        return self._file_format

    def get_file_format_str(self) -> str:
        return self._file_format_str

    def __repr__(self) -> str:
        text = 'LocalDocument: {' + self._dump()
        if self._file_path:
            text += ", file: '%s'" % self._file_path
        text += ', format: %s' % FILE_FORMAT_NAMES.get(
            int(self._file_format), 'unknown')
        return text + ", format_str: '%s'}" % self._file_format_str
