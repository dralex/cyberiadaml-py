# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The documents written by cyberiadaml-js, read by this library
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
"""The documents written by cyberiadaml-js, read by this library."""
import json
import pathlib

import pytest
from cyberiadaml_py import CGMLParser, core

EXAMPLES = pathlib.Path(__file__).resolve().parent.parent / 'examples'
WRITERS = sorted(p for p in EXAMPLES.glob('js-*') if p.is_dir())


def _documents():
    params = []
    for writer in WRITERS:
        manifest = json.loads((writer / 'manifest.json')
                              .read_text(encoding='utf-8'))
        for name in manifest['documents']:
            params.append(pytest.param(writer, name,
                                       id='%s/%s' % (writer.name, name)))
    return params


DOCUMENTS = _documents()


def test_the_documents_are_there():
    """Check the snapshot of the js-written documents is present."""
    assert WRITERS
    assert len(DOCUMENTS) >= 71


@pytest.mark.parametrize('writer,name', DOCUMENTS)
def test_strict_read_gives_the_writer_dump(writer, name):
    """Check a js-written document reads strictly to the dump of js."""
    document = core.read((writer / (name + '.graphml')).read_bytes(),
                         strict=True)
    assert document.label == core.FORMAT_STANDARD
    assert core.dump(document) == (writer / (name + '.expected.txt')) \
        .read_text(encoding='utf-8')


@pytest.mark.parametrize('writer,name', DOCUMENTS)
def test_the_1x_parser_reads_it(writer, name):
    """Check the 1.x parser of lapki-compiler reads a js-written document."""
    text = (writer / (name + '.graphml')).read_text(encoding='utf-8')
    elements = CGMLParser().parse_cgml(text)
    assert elements.state_machines
