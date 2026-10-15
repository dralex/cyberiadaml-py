# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The L1 layer: encoding checks and the position-tracking XML parse
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
"""The L1 layer: encoding checks and the position-tracking XML parse."""
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional
from xml.parsers import expat

from .findings import ERROR, INFO, WARNING
from .rules import declare

declare('xml-not-empty', None, 1, ERROR,
        'the document is a non-empty XML file')
declare('xml-well-formed', None, 1, ERROR,
        'the document is well-formed XML')
declare('doc-encoding', 'CGML-5.1-1', 1, WARNING,
        'the document encoding is UTF-8')
declare('xml-declaration', 'CGML-5.1-2', 1, WARNING,
        'the XML declaration carries version and encoding')
declare('char-escaping', 'CGML-5.2-1', 1, ERROR,
        'XML markup characters in content are escaped',
        note='detected by the well-formedness parse')
declare('data-escaping', 'CGML-6.8-7', 1, ERROR,
        'XML special characters inside dData are escaped',
        note='detected by the well-formedness parse')
declare('xml-comments', 'CGML-5.3-1', 1, INFO,
        'XML text comments are ignored',
        note='the parser drops XML comments')

# byte-order marks of the encodings the checks recognize
_BOMS = (
    (b'\x00\x00\xfe\xff', 'UTF-32BE'),
    (b'\xff\xfe\x00\x00', 'UTF-32LE'),
    (b'\xfe\xff', 'UTF-16BE'),
    (b'\xff\xfe', 'UTF-16LE'),
    (b'\xef\xbb\xbf', 'UTF-8'),
)


@dataclass
class ParsedDocument:
    """The element tree with the source positions of its elements."""

    root: ET.Element
    # element -> (line, column, element path); keyed by the element itself,
    # an id() key would outlive an element removed by the dialect pass
    info: dict = field(default_factory=dict)
    declaration: Optional[tuple] = None  # (version, encoding, standalone)

    def inherit(self, elem, donor):
        """Give an element created after the parse the position of donor."""
        if donor in self.info:
            self.info[elem] = self.info[donor]


class _TreeLoader:
    """Build an ElementTree recording source positions and element paths."""

    def __init__(self):
        self.parser = expat.ParserCreate()
        self.parser.buffer_text = True
        self.parser.StartElementHandler = self._start
        self.parser.EndElementHandler = self._end
        self.parser.CharacterDataHandler = self._text
        self.parser.XmlDeclHandler = self._decl
        self.root = None
        self.stack = []
        self.info = {}
        self.declaration = None

    def _path(self, tag, attrs):
        base = self.info[self.stack[-1]][2] if self.stack else ''
        if tag == 'data' and 'key' in attrs:
            seg = 'data[key=%s]' % attrs['key']
        elif 'id' in attrs:
            seg = '%s[id=%s]' % (tag, attrs['id'])
        else:
            seg = tag
        return '%s/%s' % (base, seg)

    def _start(self, tag, attrs):
        elem = ET.Element(tag, attrs)
        self.info[elem] = (self.parser.CurrentLineNumber,
                           self.parser.CurrentColumnNumber + 1,
                           self._path(tag, attrs))
        if self.stack:
            self.stack[-1].append(elem)
        else:
            self.root = elem
        self.stack.append(elem)

    def _end(self, tag):
        self.stack.pop()

    def _text(self, text):
        if not self.stack:
            return
        cur = self.stack[-1]
        if len(cur):
            last = cur[-1]
            last.tail = (last.tail or '') + text
        else:
            cur.text = (cur.text or '') + text

    def _decl(self, version, encoding, standalone):
        self.declaration = (version, encoding, standalone)


def _check_encoding(data, ctx):
    for bom, name in _BOMS:
        if data.startswith(bom):
            if name != 'UTF-8':
                ctx.emit('doc-encoding',
                         'the document is encoded in %s, not UTF-8' % name)
            return
    try:
        data.decode('utf-8')
    except UnicodeDecodeError as err:
        ctx.emit('doc-encoding',
                 'the document is not valid UTF-8 (%s)' % err.reason,
                 line=data.count(b'\n', 0, err.start) + 1)


def _check_declaration(loader, ctx):
    if loader.declaration is None:
        ctx.emit('xml-declaration', 'missing XML declaration', line=1,
                 column=1)
        return
    version, encoding, _ = loader.declaration
    if not version:
        ctx.emit('xml-declaration', 'the XML declaration has no version',
                 line=1, column=1)
    if not encoding:
        ctx.emit('xml-declaration', 'the XML declaration has no encoding',
                 line=1, column=1)
    elif encoding.upper() != 'UTF-8':
        ctx.emit('doc-encoding',
                 'the declared encoding is %s, not UTF-8' % encoding,
                 line=1, column=1)


def load(data, ctx):
    """Run the L1 checks; return the parsed document or None."""
    if not data or not data.strip():
        ctx.emit('xml-not-empty', 'the file is empty')
        return None
    _check_encoding(data, ctx)
    loader = _TreeLoader()
    try:
        loader.parser.Parse(data, True)
    except expat.ExpatError as err:
        ctx.emit('xml-well-formed',
                 'XML parse error: %s' % expat.errors.messages[err.code],
                 line=err.lineno, column=err.offset + 1)
        return None
    _check_declaration(loader, ctx)
    return ParsedDocument(loader.root, loader.info, loader.declaration)
