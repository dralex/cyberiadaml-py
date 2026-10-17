# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The pure-Python interface reads the examples as the binding does
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
"""The examples read with cml give the dumps the binding gave.

binding-view.json comes from tools/record_binding_view.py run with the
binding; the differences below are known and kept on purpose.
"""
import importlib.util
import json
import pathlib
import re

import pytest
from cyberiadaml_py import cml

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
_SPEC = importlib.util.spec_from_file_location(
    'record_binding_view', ROOT / 'tools' / 'record_binding_view.py')
assert _SPEC is not None and _SPEC.loader is not None
_TOOL = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_TOOL)
EXAMPLES, view = _TOOL.EXAMPLES, _TOOL.view

RECORD = json.loads((pathlib.Path(__file__).resolve().parent /
                     'binding-view.json').read_text(encoding='utf-8'))
DOCUMENTS = sorted(RECORD['documents'])
BODY = re.compile(r"(body: ')(.*?)('(?:, geometry|, subjects|\}))", re.S)

# (document, mode) -> why cml differs from the binding
KNOWN = {
    ('standard/negative/X-5.7-4-two-markers.graphml', 'lenient'):
        'a node with a vertex kind and a submachine reference is read as '
        'the vertex',
    ('lapki/client-template-blinker.graphml', 'strict'):
        'gFormat not first: refused by the core, not checked by the binding',
    ('standard/negative/X-6.7-2-dangling-link.graphml', 'strict'):
        'another exception class: the core meets the metadata first',
}
# the binding checks the metadata before anything else in its strict mode
STRICT_META = ('client-demo-blinker', 'compiler-cyberiadaformat-blinker',
               'js-demo-two-blinkers', 'lib-lapki-js', 'py-demo-two-blinkers')
for _name in STRICT_META:
    KNOWN[('lapki/%s.graphml' % _name, 'strict')] = \
        'MetainfoException in the binding, CybMLException in cml'


def _bodies(dump: str) -> str:
    # a repaired Lapki component body is written from its parameters
    return BODY.sub(lambda m: m.group(1) + m.group(2).rstrip() +
                    m.group(3), dump)


@pytest.mark.parametrize('name', DOCUMENTS)
def test_view(name):
    """Check a document reads in both modes as the binding read it."""
    actual = view(cml, EXAMPLES / name)
    for mode in ('lenient', 'strict'):
        expected = RECORD['documents'][name][mode]
        if (name, mode) in KNOWN:
            assert actual[mode] != expected, 'fixed: %s' % KNOWN[name, mode]
            continue
        assert _bodies(actual[mode]) == _bodies(expected), mode
