# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The geometry of the examples compared with the CyberiadaML binding
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
"""The geometry results of cml are those the binding gave.

binding-layout.json comes from tools/record_binding_layout.py run with the
binding: the examples read in the Qt format, saved rounded, laid out, laid
out again after an edit and updated as drawn. The differences below are
known and kept on purpose.
"""
import importlib.util
import json
import pathlib
import re

import pytest
from cyberiadaml_py import cml

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
_SPEC = importlib.util.spec_from_file_location(
    'record_binding_layout', ROOT / 'tools' / 'record_binding_layout.py')
assert _SPEC is not None and _SPEC.loader is not None
_TOOL = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_TOOL)

RECORD = json.loads((ROOT / 'tests' / 'cml' / 'binding-layout.json')
                    .read_text(encoding='utf-8'))
DOCUMENTS = sorted(RECORD['documents'])
BODY = re.compile(r"(body: ')(.*?)('[,}])", re.S)
CANONICAL_BODY = re.compile(r'(body: ")(.*?)((?:\\n| )*")')
# the documents breaking a standard rule the writer refuses: repeated ids
# across machines, siblings sharing a name
REFUSED = ('lapki/compiler-test-cyberbear.graphml',
           'lapki/compiler-two-blinkers.graphml',
           'lapki/js-demo-two-blinkers.graphml',
           'lapki/py-demo-two-blinkers.graphml')
# the known differences: the example, the scenarios, why
KNOWN = {
    'standard/negative/X-5.7-4-two-markers.graphml':
        (('qt', 'saved', 'layout', 'update', 'drawn'),
         'a node with a vertex kind and a submachine reference'),
    'lapki/compiler-test-initial-states.graphml':
        (('layout', 'update', 'drawn'),
         'the repaired component bodies size their comments'),
}


def _bodies(dump: str) -> str:
    # a repaired Lapki component body is written from its parameters
    dump = BODY.sub(lambda m: m.group(1) + m.group(2).rstrip() +
                    m.group(3), dump)
    return CANONICAL_BODY.sub(lambda m: m.group(1) + m.group(2) + '"', dump)


@pytest.mark.parametrize('name', DOCUMENTS)
def test_layout(name):
    """Check the geometry of an example comes out as with the binding."""
    expected = RECORD['documents'][name]
    actual = _TOOL.run(cml, _TOOL.EXAMPLES / name)
    for scenario, result in expected.items():
        got = actual[scenario]
        if name in KNOWN and scenario in KNOWN[name][0]:
            continue
        if scenario == 'saved' and got == 'EXC CybMLException' and \
                (name.startswith('standard/negative/') or name in REFUSED):
            continue    # the writer refuses what the standard forbids
        assert _bodies(got) == _bodies(result), scenario
