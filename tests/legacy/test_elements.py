# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The 1.6 fields of the 1.x interface: the elements of the extension profiles
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
"""The 1.6 fields of the 1.x interface: the extension elements."""
import json
import pathlib
import re

import pytest
from cyberiadaml_py import CGMLBuilder, CGMLParser, core
from cyberiadaml_py.types.cgml_scheme import CGMLDataNode, CGMLPointNode
from cyberiadaml_py.types.common import Point, Rectangle

EXAMPLES = pathlib.Path(__file__).resolve().parent.parent / 'examples'
STANDARD = EXAMPLES / 'standard'
LAPKI = EXAMPLES / 'lapki'
FIXTURES = json.loads((STANDARD / 'manifest.json')
                      .read_text(encoding='utf-8'))['fixtures']
POSITIVE = sorted(n for n, e in FIXTURES.items() if 'reject' not in e)
CORPUS = json.loads((LAPKI / 'manifest.json')
                    .read_text(encoding='utf-8'))['documents']
VALID = sorted(n for n, e in CORPUS.items() if e['status'] == 'valid')
BODY = re.compile(r'^( +body: ")((?:\\")?.*?)"$', re.M)


def _bodies(dump):
    # the 1.x texts are trimmed; a component body is written from its
    # parameters, without trailing empty lines
    def strip(match):
        text = match.group(2)
        while text.endswith('\\n'):
            text = text[:-2]
        return match.group(1) + text.strip() + '"'
    return BODY.sub(strip, dump)


def _read(path):
    return CGMLParser().parse_cgml(path.read_text(encoding='utf-8'))


def _round_trip(path):
    text = CGMLBuilder().build(_read(path))
    return core.dump(core.read(text, strict=True))


@pytest.mark.parametrize('name', POSITIVE)
def test_positive_round_trip(name):
    """Check a positive example written by the 1.x builder: same dump."""
    expected = (STANDARD / (name + '.expected.txt')).read_text(
        encoding='utf-8')
    assert _bodies(_round_trip(STANDARD / (name + '.graphml'))) == \
        _bodies(expected)


@pytest.mark.parametrize('name', VALID)
def test_lapki_round_trip(name):
    """Check a valid Lapki document written as its standard rewrite."""
    expected = (LAPKI / (name + '.expected.txt')).read_text(
        encoding='utf-8')
    assert _bodies(_round_trip(LAPKI / (name + '.graphml'))) == \
        _bodies(expected)


def test_submachine_states_and_points():
    """Check the submachine reference and the typed entry/exit points."""
    elements = _read(STANDARD / 'ext' / 'F-EXT-SUB.graphml')
    caller, callee = (elements.state_machines['M1'],
                      elements.state_machines['M2'])
    assert caller.states['sub0'].submachine == 'M2'
    assert caller.states['s1'].submachine is None
    assert list(caller.entry_points) == ['sub0::en']
    assert caller.entry_points['sub0::en'].parent == 'sub0'
    assert list(caller.exit_points) == ['sub0::ex']
    assert list(callee.entry_points) == ['m2en']
    assert caller.unknown_vertexes == {} == callee.unknown_vertexes
    keys = {d.key for s in caller.states.values()
            for d in s.unknown_datanodes}
    assert 'dSubmachineState' not in keys


def test_collapsed_state_and_link_to_a_transition():
    """Check collapsed, a region and a comment link to a transition."""
    sm = _read(STANDARD / 'ext' / 'F-EXT-C.graphml').state_machines['M1']
    assert sm.states['c0'].collapsed
    assert not sm.states['n0'].collapsed
    assert [r.id for r in sm.states['c0'].regions] == ['c0:']
    assert sm.states['cs1'].region == 'c0:'
    link = sm.links['cN-t#1']
    assert (link.target, link.pivot, link.chunk) == \
        ('n0-c0#1', 'dData', 'WORK')
    assert 'cN-t#1' not in sm.transitions


def test_regions():
    """Check the regions of a state and the region of its children."""
    sm = _read(STANDARD / 'core' / 'F-REGIONS.graphml').state_machines['G']
    assert [r.id for r in sm.states['p0'].regions] == ['p0-0:', 'p0-1:']
    assert (sm.states['r1s'].region, sm.states['r2s'].region) == \
        ('p0-0:', 'p0-1:')
    assert sm.states['n1'].region is None


def test_markup_colours_formal_names():
    """Check the markup, the colours and the formal names."""
    sm = _read(STANDARD / 'ext' / 'F-EXT-D.graphml').state_machines['G']
    assert sm.notes['cDoc'].markup == 'markdown'
    assert sm.notes['cPrompt'].type == 'formal'
    assert sm.notes['cPlain'].markup is None
    assert sm.states['n0'].color == '#FF8800'
    sm = _read(STANDARD / 'ext' / 'F-EXT-P.graphml').state_machines['G']
    assert sm.formal_name == 'platform_sm'
    assert sm.states['n0'].formal_name == 'idle_state'


def test_full_geometry():
    """Check the machine rect, the label rect, the source/target points."""
    sm = _read(STANDARD / 'geometry' / 'F-GEO-F.graphml') \
        .state_machines['G']
    assert sm.bounds == Rectangle(x=-100.5, y=-50.25, width=400.0,
                                  height=300.0)
    transition = sm.transitions['n0-n1#1']
    assert transition.label_position == Rectangle(x=60.0, y=20.0,
                                                  width=48.5, height=14.0)
    assert transition.source_point == Point(x=39.5, y=40.5)
    assert transition.target_point == Point(x=140.0, y=40.5)
    assert len(sm.transitions['n1-n1#1'].position) == 3


def test_typed_fields_win_over_the_data():
    """Check the builder takes a typed field over a 1.5-style data item."""
    elements = _read(STANDARD / 'ext' / 'F-EXT-P.graphml')
    state = elements.state_machines['G'].states['n0']
    state.unknown_datanodes.append(
        CGMLDataNode('dFormalName', 'old_name', None, None))
    state.formal_name = 'new_name'
    document = core.read(CGMLBuilder().build(elements), strict=True)
    names = {n.id: n.formal_name for n in document.machines[0].children}
    assert names['n0'] == 'new_name'


def test_a_transition_with_a_pivot_is_a_link():
    """Check a 1.4 comment link among the transitions is written as one."""
    elements = _read(STANDARD / 'ext' / 'F-EXT-C.graphml')
    sm = elements.state_machines['M1']
    link = sm.links.pop('cN-t#1')
    transition = sm.transitions['n0-c0#1']
    sm.transitions['cN-t#1'] = type(transition)(
        id='cN-t#1', source=link.source, target=link.target, actions='',
        unknown_datanodes=[CGMLDataNode('dChunk', 'WORK', None, None)],
        pivot='dData')
    again = CGMLParser().parse_cgml(CGMLBuilder().build(elements))
    written = again.state_machines['M1'].links['cN-t#1']
    assert (written.target, written.pivot, written.chunk) == \
        ('n0-c0#1', 'dData', 'WORK')


def test_private_lapki_point_is_written_as_text():
    """Check a dLapki* point given by a caller becomes the D-5 text."""
    elements = _read(LAPKI / 'client-demo-blinker.graphml')
    sm = next(iter(elements.state_machines.values()))
    component = next(iter(sm.components.values()))
    component.unknown_datanodes = [CGMLDataNode(
        'dLapkiSchemePosition', None, None, CGMLPointNode(20, 60))]
    again = CGMLParser().parse_cgml(CGMLBuilder().build(elements))
    sm = next(iter(again.state_machines.values()))
    data = next(iter(sm.components.values())).unknown_datanodes
    assert [(d.key, d.content) for d in data] == \
        [('dLapkiSchemePosition', 'x/ 20\n\ny/ 60')]
