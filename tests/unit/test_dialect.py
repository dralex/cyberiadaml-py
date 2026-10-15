# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The Lapki dialect pass: one document per repair, the standard invariance
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
"""The Lapki dialect pass: one document per repair, the standard invariance."""
import json
import pathlib

import pytest
from cyberiadaml_py.core import rules
from cyberiadaml_py.core.dump import render
from cyberiadaml_py.core.dialect import FORMAT_LAPKI, FORMAT_VALUE

from .docbuilder import GFORMAT, KEYS, META_NODE, minimal

FIXTURES = pathlib.Path(__file__).resolve().parent.parent / 'examples' / \
    'standard'

NOTE_KEYS = KEYS + """\
  <key id="dGeometry" for="node" attr.name="geometry"/>
"""


def run(data, dialect='lapki'):
    """Return run."""
    return rules.run_document(data, 'test.graphml', dialect=dialect)


def errors(ctx):
    """Return errors."""
    return [f.rule for f in ctx.report.findings if f.severity == 'ERROR']


def repairs(ctx):
    """Return repairs."""
    return [f.rule for f in ctx.report.findings if f.layer == 0]


def machine(body, gid='G', name='Test machine', meta=META_NODE,
            edgedefault=' edgedefault="directed"'):
    """Return a state machine graph around body."""
    name_data = '    <data key="dName">%s</data>\n' % name \
        if name is not None else ''
    return ('  <graph id="%s"%s>\n    <data key="dStateMachine"/>\n%s%s%s'
            '  </graph>\n' % (gid, edgedefault, name_data, meta, body))


IDLE = """\
    <node id="init">
      <data key="dVertex">initial</data>
    </node>
    <node id="n0">
      <data key="dName">Idle</data>
    </node>
    <edge id="init-n0" source="init" target="n0"/>
"""


def clean(ctx):
    """Return clean."""
    assert errors(ctx) == [], ctx.report.render_text('test.graphml')


def test_d1_later_metadata_becomes_machine_parameters():
    """Check d1 later metadata becomes machine parameters."""
    second = META_NODE.replace(
        'standardVersion/ 1.0', 'standardVersion/ 1.0\n\nplatform/ B')
    data = minimal(machines=machine(IDLE) + machine(
        IDLE.replace('"init', '"i2').replace('"n0', '"m0')
        .replace('init-n0', 'i2-m0'),
        gid='G2', name='Second', meta=second.replace('nMeta', 'nMeta2')))
    ctx = run(data)
    clean(ctx)
    assert repairs(ctx) == ['lapki-d1']
    params = ctx.dialect.machine_params['G2']
    assert [(p.name, p.value) for p in params] == \
        [('standardVersion', '1.0'), ('platform', 'B')]
    assert ctx.model.meta_comment.id == 'nMeta'


def test_d1_metadata_moves_to_the_first_machine():
    """Check d1 metadata moves to the first machine."""
    data = minimal(machines=machine(IDLE, meta='') + machine(
        IDLE.replace('"init', '"i2').replace('"n0', '"m0')
        .replace('init-n0', 'i2-m0'), gid='G2', name='Second'))
    ctx = run(data)
    clean(ctx)
    assert repairs(ctx) == ['lapki-d1']
    assert ctx.model.meta_comment is not None
    assert ctx.model.machines[0].children[0].id == 'nMeta'


def test_d1_metadata_values_repaired():
    """Check d1 metadata values repaired."""
    meta = META_NODE.replace(
        'standardVersion/ 1.0',
        'standardVersion/\n\nplatform/ A\n\nplatform/ B\n\nauthor/ undefined')
    ctx = run(minimal(machines=machine(IDLE, meta=meta)))
    clean(ctx)
    assert sorted(repairs(ctx)) == ['lapki-d1'] * 3
    assert ctx.model.param('standardVersion') == '1.0'
    assert ctx.model.param('platform') == 'A'
    assert ctx.model.param('author') is None


COMPONENT = """\
    <node id="cLED1">
      <data key="dNote">formal</data>
      <data key="dName"> CGML_COMPONENT </data>
      <data key="dData">id/ LED1

type/ LED

name/ Main

</data>
    </node>
"""


def test_d2_old_component_comment():
    """Check d2 old component comment."""
    body = COMPONENT + IDLE + \
        '    <edge id="nMeta-cLED1" source="nMeta" target="cLED1"/>\n'
    ctx = run(minimal(machines=machine(body)))
    clean(ctx)
    assert sorted(repairs(ctx)) == ['lapki-d2', 'lapki-d2']
    comment = [c for c in ctx.model.machines[0].children if c.id == 'cLED1']
    assert comment[0].name == 'CGML_COMPONENT LED1'
    assert comment[0].body == 'type/ LED\n\nname/ Main'
    assert ctx.model.machines[0].links == []


COMPOSITE = """\
    <node id="init">
      <data key="dVertex">initial</data>
    </node>
    <node id="n1">
      <data key="dName">Outer</data>
      <graph id="n1">
        <node id="n1::n2">
          <data key="dName">Inner</data>
        </node>
      </graph>
    </node>
    <edge id="init-n1" source="init" target="n1"/>
"""


def test_d3_region_graph_id():
    """Check d3 region graph id."""
    ctx = run(minimal(machines=machine(COMPOSITE)))
    clean(ctx)
    assert repairs(ctx) == ['lapki-d3']
    outer = ctx.model.machines[0].children[2]
    assert outer.regions[0].id == 'n1::region'


def test_d4_geometry_kinds():
    """Check d4 geometry kinds."""
    body = """\
    <node id="init">
      <data key="dVertex">initial</data>
      <data key="dGeometry"><rect x="10" y="20" width="-1" height="-1"/></data>
    </node>
    <node id="n0">
      <data key="dName">Idle</data>
      <data key="dGeometry"><point x="100" y="200"/></data>
    </node>
    <edge id="init-n0" source="init" target="n0"/>
"""
    ctx = run(minimal(keys=NOTE_KEYS, machines=machine(body)))
    clean(ctx)
    assert sorted(repairs(ctx)) == ['lapki-d4a', 'lapki-d4b']
    text = render(ctx.model)
    assert 'geometry: point 10.00 20.00' in text
    assert 'geometry: rect 100.00 200.00 0.00 0.00' in text


def test_d5_private_key_with_a_point():
    """Check d5 private key with a point."""
    component = COMPONENT.replace(
        '    </node>\n',
        '      <data key="dLapkiSchemePosition">'
        '<point x="20" y="60"/></data>\n'
        '    </node>\n', 1)
    ctx = run(minimal(machines=machine(component + IDLE)))
    clean(ctx)
    assert sorted(repairs(ctx)) == \
        ['lapki-d2', 'lapki-d5a', 'lapki-d5b']
    decl = [k for k in ctx.model.keys if k.id == 'dLapkiSchemePosition']
    assert decl and decl[0].for_kind == 'node'
    data = [d for d in ctx.parsed.root.iter('data')
            if d.get('key') == 'dLapkiSchemePosition']
    assert data[0].text == 'x/ 20\n\ny/ 60' and len(data[0]) == 0


def test_d6_format_label_and_position():
    """Check d6 format label and position."""
    data = minimal(gformat='', keys=KEYS + GFORMAT.replace(
        'Cyberiada-GraphML-1.0', 'Cyberiada-GraphML'))
    ctx = run(data)
    clean(ctx)
    assert repairs(ctx) == ['lapki-d6', 'lapki-d6']
    assert ctx.model.format == FORMAT_VALUE


def test_d7_structural_leniency():
    """Check d7 structural leniency."""
    second = IDLE.replace('"init"', '"i2"').replace('init-n0', 'x')
    body = IDLE + """\
    <node id="note">
      <data key="dData">a comment</data>
      <data key="dNote"></data>
    </node>
    <edge id="init-n0" source="init" target="n0"/>
"""
    data = minimal(machines=machine(body, edgedefault='') +
                   machine(second, gid='G2', name='Second', meta=''))
    ctx = run(data)
    clean(ctx)
    assert sorted(repairs(ctx)) == [
        'lapki-d7a', 'lapki-d7b', 'lapki-d7d', 'lapki-d7e', 'lapki-d7f']
    second_machine = ctx.model.machines[1]
    assert [n.id for n in second_machine.children] == ['i2', 'G2::n0']
    assert second_machine.transitions[0].target == 'G2::n0'
    edges = [t.id for t in ctx.model.machines[0].transitions]
    assert edges == ['init-n0', 'init-n0#1']


def test_d8_values():
    """Check d8 values."""
    meta = META_NODE.replace(
        'standardVersion/ 1.0',
        'standardVersion/ 1.0\n\ntransitionOrder/ transitionFirst')
    ctx = run(minimal(machines=machine(IDLE, name=None, meta=meta)))
    clean(ctx)
    assert sorted(repairs(ctx)) == ['lapki-d8a', 'lapki-d8b']
    assert ctx.model.transition_order() == 'actionFirst'
    assert ctx.model.machines[0].name == 'G'


def test_d9_function_graph():
    """Check d9 function graph."""
    function = """\
  <graph id="F" edgedefault="directed">
    <data key="dFunction"/>
    <node id="f0"/>
  </graph>
"""
    keys = KEYS + '  <key id="dFunction" for="graph" ' \
        'attr.name="function"/>\n'
    data = minimal(keys=keys, machines=machine(IDLE) + function)
    ctx = run(data)
    clean(ctx)
    assert repairs(ctx) == ['lapki-d9']
    assert [g.get('id') for g in ctx.dialect.extension_graphs] == ['F']
    assert [m.id for m in ctx.model.machines] == ['G']


def test_label():
    """Check label."""
    meta = META_NODE.replace('standardVersion/ 1.0',
                             'standardVersion/ 1.0\n\nlapkiVisual/ true')
    assert run(minimal()).dialect.label == FORMAT_VALUE
    ctx = run(minimal(machines=machine(IDLE, meta=meta)))
    assert repairs(ctx) == [] and ctx.dialect.label == FORMAT_LAPKI


def test_without_the_dialect_the_patterns_stay_errors():
    """Check without the dialect the patterns stay errors."""
    data = minimal(gformat='', keys=KEYS + GFORMAT.replace(
        'Cyberiada-GraphML-1.0', 'Cyberiada-GraphML'))
    ctx = run(data, dialect=None)
    assert ctx.dialect is None
    assert 'gformat-first' in errors(ctx)


def test_unknown_dialect():
    """Check unknown dialect."""
    with pytest.raises(ValueError):
        run(minimal(), dialect='nonexistent')


def _positives():
    manifest = json.loads((FIXTURES / 'manifest.json')
                          .read_text(encoding='utf-8'))['fixtures']
    return sorted(name for name, entry in manifest.items()
                  if 'reject' not in entry)


@pytest.mark.parametrize('name', _positives())
def test_standard_examples_are_untouched(name):
    """Check standard examples are untouched."""
    data = (FIXTURES / (name + '.graphml')).read_bytes()
    ctx = run(data)
    assert repairs(ctx) == []
    expected = (FIXTURES / (name + '.expected.txt')).read_text(
        encoding='utf-8')
    assert render(ctx.model) == expected
