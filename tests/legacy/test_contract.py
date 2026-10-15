# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The 1.x contract: the fields lapki-compiler reads, the builder
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
"""The 1.x contract: the fields lapki-compiler reads, the builder.

The recorded view lapki-compiler-view.json was compared with the output of
cyberiadaml-py 1.4.1 when recorded; re-record it with
python3 -m tests.legacy.test_contract and review the difference.
"""
import json
import pathlib

import pytest
from cyberiadaml_py import CGMLBuilder, CGMLParser, core
from cyberiadaml_py.cyberiadaml_builder import CGMLBuilderException
from cyberiadaml_py.cyberiadaml_parser import CGMLParserException

HERE = pathlib.Path(__file__).resolve().parent
CORPUS = HERE.parent / 'examples' / 'lapki'
VIEW = HERE / 'lapki-compiler-view.json'
DOCUMENTS = json.loads((CORPUS / 'manifest.json')
                       .read_text(encoding='utf-8'))['documents']
VALID = sorted(n for n, e in DOCUMENTS.items() if e['status'] == 'valid')
VERTICES = ('initial_states', 'choices', 'finals', 'shallow_history',
            'deep_history')


def view(elements):
    """Return the fields lapki-compiler reads, as JSON data."""
    out = {}
    for sm_id, sm in elements.state_machines.items():
        out[sm_id] = {
            'platform': sm.platform,
            'meta': dict(sm.meta.values),
            'name': sm.name,
            'states': {k: [v.name, v.actions, v.parent]
                       for k, v in sm.states.items()},
            'transitions': {k: [v.source, v.target, v.actions]
                            for k, v in sm.transitions.items()},
            'vertices': {f: {k: v.parent
                             for k, v in getattr(sm, f).items()}
                         for f in VERTICES},
            'components': {k: [v.id, v.type, dict(v.parameters)]
                           for k, v in sm.components.items()},
        }
    return out


def _parse(name):
    return CGMLParser().parse_cgml(
        (CORPUS / (name + '.graphml')).read_text(encoding='utf-8'))


@pytest.mark.parametrize('name', sorted(DOCUMENTS))
def test_lapki_compiler_view(name):
    """Check the fields lapki-compiler reads against the recorded view."""
    recorded = json.loads(VIEW.read_text(encoding='utf-8'))
    assert view(_parse(name)) == recorded[name]


@pytest.mark.parametrize('name', VALID)
def test_built_document_is_standard(name):
    """Check the builder writes a standard document of the elements."""
    elements = _parse(name)
    text = CGMLBuilder().build(elements)
    core.read(text, strict=True)
    again = CGMLParser().parse_cgml(text)
    for sm_id, sm in again.state_machines.items():
        first = elements.state_machines[sm_id]
        assert sm.platform == first.platform
        assert sm.meta.values == first.meta.values
        assert len(sm.states) == len(first.states)
        assert len(sm.transitions) == len(first.transitions)


@pytest.mark.parametrize('name', [n for n in VALID if 'two-blinkers'
                                  not in n and n != 'client-demo-blinker'])
def test_round_trip(name):
    """Check parse, build and parse give the same elements."""
    elements = _parse(name)
    assert CGMLParser().parse_cgml(CGMLBuilder().build(elements)) == \
        elements


def test_ids_of_later_machines_are_made_unique():
    """Check ids repeated in a later machine get the machine prefix."""
    elements = _parse('compiler-two-blinkers')
    assert sorted(elements.state_machines['Oa'].states) == \
        ['diod1', 'diod2']
    again = CGMLParser().parse_cgml(CGMLBuilder().build(elements))
    assert sorted(again.state_machines['Oa'].states) == \
        ['Oa::diod1', 'Oa::diod2']


def test_unreadable_document():
    """Check an unreadable document raises CGMLParserException."""
    with pytest.raises(CGMLParserException):
        CGMLParser().parse_cgml('<graphml')


def test_unknown_parent():
    """Check a state under a missing parent raises CGMLBuilderException."""
    elements = _parse('compiler-ms1-btn')
    sm = list(elements.state_machines.values())[0]
    list(sm.states.values())[0].parent = 'missing'
    with pytest.raises(CGMLBuilderException):
        CGMLBuilder().build(elements)


def test_comment_without_geometry_and_links():
    """Check a geometry-less comment and a link are read the 1.5 way."""
    data = (HERE.parent / 'examples' / 'standard' / 'core' /
            'F-CMT.graphml').read_text(encoding='utf-8')
    elements = CGMLParser().parse_cgml(data)
    sm = list(elements.state_machines.values())[0]
    assert any(n.position is None for n in sm.notes.values())
    assert all(not any(d.key == 'dPivot' for d in t.unknown_datanodes)
               for t in sm.transitions.values())


if __name__ == '__main__':
    VIEW.write_text(json.dumps({n: view(_parse(n)) for n in sorted(DOCUMENTS)},
                               ensure_ascii=False, indent=1) + '\n',
                    encoding='utf-8')
