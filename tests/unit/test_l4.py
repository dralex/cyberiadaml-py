# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The L4 layer tests: document integrity
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
"""The L4 layer tests: document integrity."""
from cyberiadaml_py.core import rules

from .docbuilder import KEYS, META_NODE, minimal

SECOND_MACHINE = """\
  <graph id="G2" edgedefault="directed">
    <data key="dStateMachine"/>
    <data key="dName">Second machine</data>
    <node id="g2n0">
      <data key="dName">Idle</data>
    </node>
  </graph>
"""


def run(data):
    """Return run."""
    return rules.run_document(data, 'test.graphml')


def errors(ctx):
    """Return errors."""
    return [f.rule for f in ctx.report.findings if f.severity == 'ERROR']


def warnings(ctx):
    """Return warnings."""
    return [f.rule for f in ctx.report.findings if f.severity == 'WARNING']


def multi(second=SECOND_MACHINE):
    """Return multi."""
    from .docbuilder import MACHINE
    return minimal(machines=MACHINE + second)


def test_minimal_document_clean_at_l4():
    """Check minimal document clean at L4."""
    ctx = run(minimal())
    assert ctx.report.findings == []
    assert ctx.report.layers_run == [1, 2, 3, 4]


def test_multi_machine_document_accepted():
    """Check multi machine document accepted."""
    ctx = run(multi())
    assert errors(ctx) == []


def test_duplicate_data_key_rejected():
    """Check duplicate data key rejected."""
    doc = minimal().replace(
        b'      <data key="dName">Idle</data>',
        b'      <data key="dName">Idle</data>\n'
        b'      <data key="dName">Idle again</data>')
    assert 'unique-data-keys' in errors(run(doc))


def test_document_without_graphs_rejected():
    """Check document without graphs rejected."""
    text = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">\n'
            '  <data key="gFormat">Cyberiada-GraphML-1.0</data>\n' +
            KEYS + '</graphml>\n')
    assert 'top-level-graphs' in errors(run(text.encode()))


def test_duplicate_ids_across_machines_rejected():
    """Check duplicate ids across machines rejected."""
    doc = multi(SECOND_MACHINE.replace('id="g2n0"', 'id="n0"'))
    assert 'unique-ids' in errors(run(doc))


def test_node_id_equal_to_region_id_rejected():
    """Check node id equal to region id rejected."""
    machines = """\
  <graph id="G" edgedefault="directed">
    <data key="dStateMachine"/>
    <data key="dName">Test machine</data>
%s\
    <node id="c0">
      <data key="dName">Composite</data>
      <graph id="dup">
        <data key="dRegion"/>
        <node id="dup"><data key="dName">Child</data></node>
      </graph>
    </node>
  </graph>
""" % META_NODE
    assert 'unique-ids' in errors(run(minimal(machines=machines)))


def test_duplicate_edge_id_rejected():
    """Check duplicate edge id rejected."""
    doc = minimal().replace(
        b'<edge id="init-n0#1" source="init" target="n0"/>',
        b'<edge id="init-n0#1" source="init" target="n0"/>\n'
        b'    <edge id="init-n0#1" source="n0" target="n0"/>')
    assert 'unique-ids' in errors(run(doc))


def test_graph_without_statemachine_marker_rejected():
    """Check graph without statemachine marker rejected."""
    doc = minimal().replace(b'    <data key="dStateMachine"/>\n', b'')
    assert 'sm-marker' in errors(run(doc))


def test_sm_name_variants_rejected():
    """Check sm name variants rejected."""
    # missing dName
    doc = minimal().replace(b'    <data key="dName">Test machine</data>\n',
                            b'')
    assert 'sm-name' in errors(run(doc))
    # empty dName
    doc = minimal().replace(b'    <data key="dName">Test machine</data>',
                            b'    <data key="dName"></data>')
    assert 'sm-name' in errors(run(doc))
    # two machines with equal names
    doc = multi(SECOND_MACHINE.replace('Second machine', 'Test machine'))
    assert 'sm-name' in errors(run(doc))


def test_sibling_states_with_equal_names_rejected():
    """Check sibling states with equal names rejected."""
    doc = minimal().replace(
        b'  </graph>',
        b'    <node id="n1"><data key="dName">Idle</data></node>\n  </graph>')
    assert 'state-names' in errors(run(doc))


def test_same_name_on_different_levels_accepted():
    """Check same name on different levels accepted."""
    machines = """\
  <graph id="G" edgedefault="directed">
    <data key="dStateMachine"/>
    <data key="dName">Test machine</data>
%s\
    <node id="c0">
      <data key="dName">Idle</data>
      <graph id="c0:">
        <data key="dRegion"/>
        <node id="c1"><data key="dName">Idle</data></node>
      </graph>
    </node>
  </graph>
""" % META_NODE
    ctx = run(minimal(machines=machines))
    assert errors(ctx) == []


def test_transition_to_missing_node_rejected():
    """Check transition to missing node rejected."""
    doc = minimal().replace(b'target="n0"/>', b'target="nowhere"/>')
    assert 'transition-endpoints' in errors(run(doc))


def test_transition_to_other_machine_rejected():
    """Check transition to other machine rejected."""
    doc = multi().replace(b'<edge id="init-n0#1" source="init" '
                          b'target="n0"/>',
                          b'<edge id="init-n0#1" source="init" '
                          b'target="g2n0"/>')
    assert 'transition-endpoints' in errors(run(doc))


def test_transition_to_the_machine_graph_rejected():
    """Check transition to the machine graph rejected."""
    doc = minimal().replace(b'target="n0"/>', b'target="G"/>')
    assert 'transition-endpoints' in errors(run(doc))


def test_plain_transition_targeting_edge_rejected():
    """Check plain transition targeting edge rejected."""
    doc = minimal().replace(
        b'  </graph>',
        b'    <edge id="n0-e#1" source="n0" target="init-n0#1"/>\n  </graph>')
    assert 'link-target' in errors(run(doc))


def test_comment_link_accepted_and_resolved():
    """Check comment link accepted and resolved."""
    doc = minimal().replace(
        b'    <edge id="init-n0#1"',
        b'    <node id="c0">\n      <data key="dNote">informal</data>\n'
        b'    </node>\n    <edge id="init-n0#1"').replace(
        b'  </graph>',
        b'    <edge id="c0-n0#1" source="c0" target="n0">\n'
        b'      <data key="dPivot">dName</data>\n'
        b'      <data key="dChunk">Idle</data>\n'
        b'    </edge>\n  </graph>')
    ctx = run(doc)
    assert ctx.report.findings == []


def test_comment_link_to_missing_node_rejected():
    """Check comment link to missing node rejected."""
    doc = minimal().replace(
        b'  </graph>',
        b'    <edge id="nMeta-x#1" source="nMeta" target="nowhere">\n'
        b'      <data key="dPivot">dName</data>\n'
        b'      <data key="dChunk">Idle</data>\n'
        b'    </edge>\n  </graph>')
    assert 'link-endpoints' in errors(run(doc))


def test_comment_link_from_non_comment_rejected():
    """Check comment link from non comment rejected."""
    doc = minimal().replace(
        b'  </graph>',
        b'    <edge id="n0-m#1" source="n0" target="init">\n'
        b'      <data key="dPivot">dName</data>\n'
        b'      <data key="dChunk">Idle</data>\n'
        b'    </edge>\n  </graph>')
    assert 'link-source' in errors(run(doc))


def test_double_else_from_state_reported():
    """Check double else from state reported."""
    doc = minimal().replace(
        b'  </graph>',
        b'    <edge id="n0-init#1" source="n0" target="init">\n'
        b'      <data key="dData">[else]/ a()</data>\n'
        b'    </edge>\n'
        b'    <edge id="n0-init#2" source="n0" target="init">\n'
        b'      <data key="dData">[else]/ b()</data>\n'
        b'    </edge>\n  </graph>')
    ctx = run(doc)
    assert 'single-else' in errors(ctx)


def test_double_else_from_choice_reported():
    """Check double else from choice reported."""
    doc = minimal().replace(
        b'  </graph>',
        b'    <node id="ch0"><data key="dVertex">choice</data></node>\n'
        b'    <edge id="ch0-init#1" source="ch0" target="init">\n'
        b'      <data key="dData">[else]/ a()</data>\n'
        b'    </edge>\n'
        b'    <edge id="ch0-n0#1" source="ch0" target="n0">\n'
        b'      <data key="dData">[else]/ b()</data>\n'
        b'    </edge>\n  </graph>')
    # the node phase is over after the first edge: build a well-ordered doc
    doc = minimal().replace(
        b'    <edge id="init-n0#1" source="init" target="n0"/>',
        b'    <node id="ch0"><data key="dVertex">choice</data></node>\n'
        b'    <edge id="init-n0#1" source="init" target="n0"/>\n'
        b'    <edge id="ch0-init#1" source="ch0" target="init">\n'
        b'      <data key="dData">[else]/ a()</data>\n'
        b'    </edge>\n'
        b'    <edge id="ch0-n0#1" source="ch0" target="n0">\n'
        b'      <data key="dData">[else]/ b()</data>\n'
        b'    </edge>')
    ctx = run(doc)
    assert 'choice-single-else' in errors(ctx)


def test_two_initials_on_one_level_rejected():
    """Check two initials on one level rejected."""
    doc = minimal().replace(
        b'    <node id="n0">',
        b'    <node id="init2"><data key="dVertex">initial</data></node>\n'
        b'    <node id="n0">')
    assert 'single-initial' in errors(run(doc))


def test_initials_on_different_levels_accepted():
    """Check initials on different levels accepted."""
    machines = """\
  <graph id="G" edgedefault="directed">
    <data key="dStateMachine"/>
    <data key="dName">Test machine</data>
%s\
    <node id="init"><data key="dVertex">initial</data></node>
    <node id="c0">
      <data key="dName">Composite</data>
      <graph id="c0:">
        <data key="dRegion"/>
        <node id="rinit"><data key="dVertex">initial</data></node>
      </graph>
    </node>
  </graph>
""" % META_NODE
    ctx = run(minimal(machines=machines))
    assert ctx.report.findings == []


def test_missing_meta_rejected():
    """Check missing meta rejected."""
    doc = minimal().replace(META_NODE.encode(), b'')
    assert 'meta-presence' in errors(run(doc))


def test_meta_in_second_machine_only_rejected():
    """Check meta in second machine only rejected."""
    from .docbuilder import MACHINE
    first = MACHINE.replace(META_NODE, '')
    second = SECOND_MACHINE.replace(
        '    <node id="g2n0">',
        META_NODE.replace('id="nMeta"', 'id="g2Meta"') +
        '    <node id="g2n0">')
    ctx = run(minimal(machines=first + second))
    assert 'meta-presence' in errors(ctx)


def test_edge_geometry_in_short_mode_reported():
    """Check edge geometry in short mode reported."""
    meta = META_NODE.replace('standardVersion/ 1.0',
                             'standardVersion/ 1.0\n\ngeometry/ short')
    doc = minimal().replace(META_NODE.encode(), meta.encode())
    doc = doc.replace(
        b'<edge id="init-n0#1" source="init" target="n0"/>',
        b'<edge id="init-n0#1" source="init" target="n0">\n'
        b'      <data key="dGeometry"><point x="1" y="2"/></data>\n'
        b'    </edge>')
    ctx = run(doc)
    assert 'edge-geometry-mode' in warnings(ctx)


def test_wrong_geometry_kind_reported():
    """Check wrong geometry kind reported."""
    # point on a state
    doc = minimal().replace(
        b'      <data key="dName">Idle</data>',
        b'      <data key="dName">Idle</data>\n'
        b'      <data key="dGeometry"><point x="1" y="2"/></data>')
    assert 'state-geometry-kind' in warnings(run(doc))
    # rect on an initial pseudostate
    doc = minimal().replace(
        b'      <data key="dVertex">initial</data>',
        b'      <data key="dVertex">initial</data>\n'
        b'      <data key="dGeometry">'
        b'<rect x="1" y="2" width="3" height="4"/></data>')
    assert 'vertex-geometry-kind' in warnings(run(doc))


def test_transition_geometry_without_endpoint_geometry_reported():
    """Check transition geometry without endpoint geometry reported."""
    doc = minimal().replace(
        b'<edge id="init-n0#1" source="init" target="n0"/>',
        b'<edge id="init-n0#1" source="init" target="n0">\n'
        b'      <data key="dLabelGeometry"><point x="1" y="2"/></data>\n'
        b'    </edge>')
    ctx = run(doc)
    assert 'transition-geometry-endpoints' in warnings(ctx)
