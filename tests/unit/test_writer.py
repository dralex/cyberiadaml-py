# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The writer of the core
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
"""The writer of the core."""
import xml.etree.ElementTree as ET

import pytest
from cyberiadaml_py import core

from .docbuilder import KEYS, META_NODE, minimal

COMPOSITE = """\
  <graph id="G" edgedefault="directed">
    <data key="dStateMachine"/>
    <data key="dName">Composite</data>
%s\
    <node id="note">
      <data key="dNote">informal</data>
      <data key="dData">see Outer</data>
    </node>
    <node id="n1">
      <data key="dName">Outer</data>
      <data key="dCollapsed"/>
      <data key="dLapkiFlag">on</data>
      <graph id="first">
        <data key="dRegion"/>
        <node id="a"><data key="dName">A</data></node>
      </graph>
      <graph id="second">
        <data key="dRegion"/>
        <node id="b"><data key="dName">B</data></node>
      </graph>
    </node>
    <edge id="note-n1" source="note" target="n1">
      <data key="dPivot"/>
    </edge>
  </graph>
""" % META_NODE

FLAG_KEY = '  <key id="dLapkiFlag" for="node" attr.name="flag" ' \
    'attr.type="string"/>\n'


def _tree(text):
    root = ET.fromstring(text.encode('utf-8'))
    for elem in root.iter():
        elem.tag = elem.tag.split('}')[-1]
    return root


def test_composite_document():
    """Check regions, collapsed states, links and extension data."""
    document = core.read(minimal(keys=KEYS + FLAG_KEY, machines=COMPOSITE),
                         strict=True)
    text = core.write(document)
    again = core.read(text, strict=True)
    assert core.dump(again) == core.dump(document)
    root = _tree(text)
    keys = [(k.get('id'), k.get('for'), k.get('attr.name'))
            for k in root if k.tag == 'key']
    assert keys == [(k.id, k.for_kind, k.attr_name) for k in document.keys]
    assert [c.tag for c in root][0] == 'data'
    outer = [n for n in root.iter('node') if n.get('id') == 'n1'][0]
    assert [g.get('id') for g in outer if g.tag == 'graph'] == \
        ['first', 'second']
    assert [d.get('key') for d in outer if d.tag == 'data'] == \
        ['dName', 'dCollapsed', 'dLapkiFlag']


def test_metadata_first_and_once():
    """Check the metadata node opens the first machine only."""
    document = core.read(minimal(), strict=True)
    machine = document.machines[0]
    machine.children.append(machine.children.pop(0))
    root = _tree(core.write(document))
    first = [g for g in root if g.tag == 'graph'][0]
    assert [n.get('id') for n in first if n.tag == 'node'][0] == 'nMeta'


def test_metadata_from_parameters():
    """Check a model without a metadata node gets one from meta_params."""
    document = core.read(minimal(), strict=True)
    machine = document.machines[0]
    machine.children.remove(document.meta_comment)
    document.meta_comment = None
    document.meta_params = [core.Param('standardVersion', '1.0', 0),
                            core.Param('name', 'Built', 2)]
    again = core.read(core.write(document), strict=True)
    assert again.param('name') == 'Built'
    assert document.meta_comment is None


def test_generated_region_ids():
    """Check regions without an id get <state id>::region ids."""
    document = core.read(minimal(keys=KEYS + FLAG_KEY, machines=COMPOSITE),
                         strict=True)
    outer = [n for n in document.machines[0].children if n.id == 'n1'][0]
    for region in outer.regions:
        region.id = None
    root = _tree(core.write(document))
    node = [n for n in root.iter('node') if n.get('id') == 'n1'][0]
    assert [g.get('id') for g in node if g.tag == 'graph'] == \
        ['n1::region', 'n1::region-2']


def test_numbers():
    """Check the shortest round-trip form of the coordinates."""
    document = core.read(minimal(), strict=True)
    state = [n for n in document.machines[0].children if n.id == 'n0'][0]
    state.geometry = core.Rect(10.0, 2.5, 100.0, 0.1)
    root = _tree(core.write(document))
    rect = [r for r in root.iter('rect')][0]
    assert dict(rect.attrib) == {'x': '10', 'y': '2.5', 'width': '100',
                                 'height': '0.1'}


def test_broken_model_is_refused():
    """Check a transition to a missing node is refused."""
    document = core.read(minimal(), strict=True)
    document.machines[0].transitions[0].target = 'missing'
    with pytest.raises(core.CGMLError) as error:
        core.write(document)
    assert 'CGML-6.3-2' in {f.req for f in error.value.findings}


def test_key_declarations():
    """Check declared keys are kept, missing extension keys declared."""
    document = core.read(minimal(keys=KEYS + FLAG_KEY, machines=COMPOSITE),
                         strict=True)
    document.keys = [k for k in document.keys if k.id != 'dLapkiFlag']
    root = _tree(core.write(document))
    keys = [(k.get('id'), k.get('for')) for k in root if k.tag == 'key']
    assert keys[-1] == ('dLapkiFlag', 'node')
    assert ('dCollapsed', 'node') not in keys
    document.keys = []
    root = _tree(core.write(document))
    keys = [(k.get('id'), k.get('for'), k.get('attr.name'))
            for k in root if k.tag == 'key']
    assert ('dCollapsed', 'node', 'collapsed') in keys
    assert ('gFormat', 'graphml', 'format') == keys[0]
