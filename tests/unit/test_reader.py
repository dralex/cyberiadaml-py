# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The reader of the core: the modes, the fatal findings, the additions
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
"""The reader of the core: the modes, the fatal findings, the additions."""
import pytest
from cyberiadaml_py import core

from .docbuilder import KEYS, META_NODE, minimal

TWINS = """\
  <graph id="G" edgedefault="directed">
    <data key="dStateMachine"/>
    <data key="dName">Twins</data>
%s\
    <node id="a">
      <data key="dName">Same</data>
    </node>
    <node id="b">
      <data key="dName">Same</data>
    </node>
  </graph>
""" % META_NODE

RICH_KEYS = KEYS + """\
  <key id="dLapkiNoteFormat" for="node" attr.name="noteFormat"
       attr.type="string"/>
"""

RICH = """\
  <graph id="G" edgedefault="directed">
    <data key="dStateMachine"/>
    <data key="dName">Rich</data>
%s\
    <node id="cLED">
      <data key="dNote">formal</data>
      <data key="dName">CGML_COMPONENT LED1</data>
      <data key="dData">type/ LED

pin/ 13</data>
    </node>
    <node id="n1">
      <data key="dName">Outer</data>
      <graph id="n1::r">
        <node id="n1::n2">
          <data key="dName">Inner</data>
          <data key="dLapkiNoteFormat">bgColor/ red</data>
        </node>
      </graph>
    </node>
    <edge id="n1-n1::n2" source="n1" target="n1::n2"/>
  </graph>
""" % META_NODE


def test_permissive_keeps_an_error():
    """Check a permissive read keeps an ERROR finding."""
    document = core.read(minimal(machines=TWINS))
    errors = [f.req for f in document.findings if f.severity == core.ERROR]
    assert errors == ['CGML-6.2-3']


def test_strict_raises_on_an_error():
    """Check a strict read raises on an ERROR finding."""
    with pytest.raises(core.CGMLError) as error:
        core.read(minimal(machines=TWINS), strict=True)
    assert 'CGML-6.2-3' in str(error.value)


@pytest.mark.parametrize('data', [b'', b'<graphml>', b'<other/>'])
def test_fatal_in_both_modes(data):
    """Check an unreadable document raises in both modes."""
    for strict in (False, True):
        with pytest.raises(core.CGMLError):
            core.read(data, strict=strict)


def test_no_state_machine_is_fatal():
    """Check a document without a state machine raises."""
    with pytest.raises(core.CGMLError) as error:
        core.read(minimal(machines=''))
    assert 'CGML-5.6-2' in {f.req for f in error.value.findings}


def test_duplicate_ids_are_fatal():
    """Check duplicate node ids in one machine raise."""
    with pytest.raises(core.CGMLError):
        core.read(minimal(machines=TWINS.replace('"b"', '"a"')))


def test_text_input():
    """Check the reader takes text as well as bytes."""
    document = core.read(minimal().decode('utf-8'))
    assert document.machines[0].name == 'Test machine'


def test_parents_lines_and_extensions():
    """Check the parents, the source lines and the extension data."""
    document = core.read(minimal(keys=RICH_KEYS, machines=RICH))
    machine = document.machines[0]
    outer = [n for n in machine.children if n.id == 'n1'][0]
    region = outer.regions[0]
    inner = region.children[0]
    assert outer.parent is machine and region.parent is outer
    assert inner.parent is region
    assert machine.transitions[0].parent is machine
    assert inner.line is not None and inner.line > outer.line
    assert [(e.key, e.text) for e in inner.extensions] == \
        [('dLapkiNoteFormat', 'bgColor/ red')]
    assert outer.extensions == []


def test_component():
    """Check the component of a component comment."""
    document = core.read(minimal(keys=RICH_KEYS, machines=RICH))
    comments = {n.id: n for n in document.machines[0].children
                if isinstance(n, core.Comment)}
    ident, kind, params = comments['cLED'].component()
    assert (ident, kind) == ('LED1', 'LED')
    assert [(p.name, p.value) for p in params] == [('pin', '13')]
    assert comments['nMeta'].component() is None
    assert document.meta_id == 'nMeta'


def test_label_and_machine_parameters():
    """Check the format label and the per-machine parameters (D-1)."""
    document = core.read(minimal())
    assert document.label == core.FORMAT_STANDARD
    assert document.machines[0].params == []
    second = META_NODE.replace('nMeta', 'nMeta2').replace(
        'standardVersion/ 1.0', 'standardVersion/ 1.0\n\nplatform/ B')
    machines = TWINS.replace('"b"', '"c"').replace('>Same<', '>A<', 1) + \
        TWINS.replace('"G"', '"G2"').replace('Twins', 'Other').replace(
            META_NODE, second).replace('"a"', '"x"').replace('"b"', '"y"')
    document = core.read(minimal(machines=machines))
    assert document.label == core.FORMAT_LAPKI
    params = document.machines[1].params
    assert [(p.name, p.value) for p in params][-1] == ('platform', 'B')
