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
import pathlib
from typing import List, Optional, Tuple

from . import errors
from .elements import Comment, Element, ElementCollection, StateMachine
from .enums import (DocumentEventPropagation, DocumentFormat,
                    DocumentGeometryDeclaration, DocumentGeometryFormat,
                    DocumentTransitionOrder, docEventPropagationBlock,
                    docEventPropagationNone, docEventPropagationPropagate,
                    elementRoot, elementSM, formatCyberiada10, formatDetect,
                    formatLapki, geometryDeclarationAbsent,
                    geometryFormatNone, geometryFormatQt,
                    transitionOrderAction, transitionOrderExit,
                    transitionOrderNone)

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
    """A document: Document(format=geometryFormatNone)."""

    def __init__(self, format: DocumentGeometryFormat =
                 DocumentGeometryFormat(geometryFormatNone)) -> None:
        super().__init__(None, elementRoot, '', '')
        self._init(format)

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
    """A document with its file: LocalDocument()."""

    def __init__(self) -> None:
        super().__init__()
        self._file_path = ''
        self._file_format = DocumentFormat(formatCyberiada10)
        self._file_format_str = ''

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
