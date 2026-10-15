# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The L2 layer tests: the admissible tag tree
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
"""The L2 layer tests: the admissible tag tree."""
from cyberiadaml_py.core import rules

from .docbuilder import GFORMAT, KEYS, META_NODE, minimal


def run(data):
    """Return run."""
    return rules.run_document(data, 'test.graphml')


def rule_names(ctx):
    """Return rule names."""
    return [f.rule for f in ctx.report.findings]


def errors(ctx):
    """Return errors."""
    return [f.rule for f in ctx.report.findings if f.severity == 'ERROR']


# a state machine with a composite state and its transition at the top level
HIERARCHY = """\
  <graph id="G" edgedefault="directed">
    <data key="dStateMachine"/>
    <data key="dName">Test machine</data>
%s\
    <node id="init">
      <data key="dVertex">initial</data>
    </node>
    <node id="n0">
      <data key="dName">Composite</data>
      <graph id="n0:">
        <data key="dRegion"/>
        <node id="n0::n1">
          <data key="dName">Child</data>
        </node>
%s\
      </graph>
%s\
    </node>
    <edge id="init-n0#1" source="init" target="n0"/>
    <edge id="n0-n1#1" source="n0" target="n0::n1"/>
  </graph>
""" % ('%s', '%s', '%s')


def hierarchy(meta=META_NODE, region_extra='', node_extra=''):
    """Return hierarchy."""
    return minimal(machines=HIERARCHY % (meta, region_extra, node_extra))


def test_minimal_document_clean_at_l2():
    """Check minimal document clean at L2."""
    ctx = run(minimal())
    assert ctx.report.findings == []
    assert 2 in ctx.report.layers_run


def test_hierarchy_document_accepted():
    """Check hierarchy document accepted."""
    ctx = run(hierarchy())
    assert ctx.report.findings == []


def test_two_regions_accepted():
    """Check two regions accepted."""
    second = """\
      <graph id="n0:2">
        <data key="dRegion"/>
        <node id="n0::n2">
          <data key="dName">Other child</data>
        </node>
      </graph>
"""
    ctx = run(hierarchy(node_extra=second))
    assert ctx.report.findings == []


def test_wrong_root_tag_rejected():
    """Check wrong root tag rejected."""
    doc = minimal().replace(b'<graphml ', b'<gml ').replace(b'</graphml>',
                                                            b'</gml>')
    ctx = run(doc)
    assert 'root-graphml' in errors(ctx)


def test_missing_xmlns_rejected():
    """Check missing xmlns rejected."""
    doc = minimal().replace(
        b' xmlns="http://graphml.graphdrawing.org/xmlns"', b'')
    ctx = run(doc)
    assert 'root-graphml' in errors(ctx)


def test_extra_namespace_tolerated():
    """Check extra namespace tolerated."""
    doc = minimal().replace(
        b'<graphml xmlns=',
        b'<graphml xmlns:y="http://www.yworks.com/xml/graphml" xmlns=')
    ctx = run(doc)
    assert rule_names(ctx) == ['extra-namespaces']
    assert ctx.report.valid()


def test_missing_gformat_rejected():
    """Check missing gformat rejected."""
    ctx = run(minimal(gformat=''))
    assert 'gformat-first' in errors(ctx)


def test_gformat_after_keys_rejected():
    """Check gformat after keys rejected."""
    ctx = run(minimal(gformat='', keys=KEYS + GFORMAT))
    assert errors(ctx) == ['gformat-first']


def test_node_inside_graphml_rejected():
    """Check node inside graphml rejected."""
    doc = minimal().replace(
        b'</graphml>', b'<node id="stray"/>\n</graphml>')
    ctx = run(doc)
    assert 'node-placement' in errors(ctx)


def test_key_after_graphs_rejected():
    """Check key after graphs rejected."""
    doc = minimal().replace(
        b'</graphml>',
        b'<key id="dChunk" for="edge" attr.name="chunk"/>\n</graphml>')
    ctx = run(doc)
    assert 'key-placement' in errors(ctx)


def test_subgraph_inside_graph_rejected():
    """Check subgraph inside graph rejected."""
    extra = '    <graph id="sub"><data key="dRegion"/></graph>\n'
    doc = minimal().replace(b'  </graph>', extra.encode() + b'  </graph>')
    ctx = run(doc)
    assert 'graph-in-graph' in errors(ctx)


def test_edge_between_nodes_reported():
    """Check edge between nodes reported."""
    doc = minimal().replace(
        b'    <node id="n0">',
        b'    <edge id="e-early#1" source="init" target="init"/>\n'
        b'    <node id="n0">')
    ctx = run(doc)
    assert 'edge-block' in rule_names(ctx)
    assert not ctx.report.has_errors()


def test_data_after_node_rejected():
    """Check data after node rejected."""
    doc = minimal().replace(
        b'  </graph>',
        b'    <data key="dName">Late name</data>\n  </graph>')
    ctx = run(doc)
    assert 'sm-child-order' in errors(ctx)


def test_statemachine_not_first_key_rejected():
    """Check statemachine not first key rejected."""
    doc = minimal().replace(
        b'    <data key="dStateMachine"/>\n'
        b'    <data key="dName">Test machine</data>',
        b'    <data key="dName">Test machine</data>\n'
        b'    <data key="dStateMachine"/>')
    ctx = run(doc)
    assert 'sm-first-key' in errors(ctx)


def test_name_before_vertex_rejected():
    """Check name before vertex rejected."""
    doc = minimal().replace(
        b'      <data key="dVertex">initial</data>',
        b'      <data key="dName">Init</data>\n'
        b'      <data key="dVertex">initial</data>')
    ctx = run(doc)
    assert 'vertex-first-key' in errors(ctx)


def test_name_before_note_rejected():
    """Check name before note rejected."""
    bad_meta = META_NODE.replace(
        '      <data key="dNote">formal</data>\n'
        '      <data key="dName">CGML_META</data>',
        '      <data key="dName">CGML_META</data>\n'
        '      <data key="dNote">formal</data>')
    ctx = run(minimal(machines=minimal_machine_with(bad_meta)))
    assert 'note-first-key' in errors(ctx)


def minimal_machine_with(meta):
    """Return minimal machine with."""
    from .docbuilder import MACHINE
    return MACHINE.replace(META_NODE, meta)


def test_pivot_not_first_key_rejected():
    """Check pivot not first key rejected."""
    doc = minimal().replace(
        b'<edge id="init-n0#1" source="init" target="n0"/>',
        b'<edge id="init-n0#1" source="init" target="n0">\n'
        b'      <data key="dChunk">Idle</data>\n'
        b'      <data key="dPivot">dName</data>\n'
        b'    </edge>')
    ctx = run(doc)
    assert 'pivot-first-key' in errors(ctx)


def test_edge_inside_region_rejected():
    """Check edge inside region rejected."""
    edge = '        <edge id="inner#1" source="n0::n1" target="n0::n1"/>\n'
    ctx = run(hierarchy(region_extra=edge))
    assert 'region-no-edges' in errors(ctx)


def test_node_inside_node_rejected():
    """Check node inside node rejected."""
    doc = minimal().replace(
        b'    <node id="n0">\n      <data key="dName">Idle</data>\n'
        b'    </node>',
        b'    <node id="n0">\n      <data key="dName">Idle</data>\n'
        b'      <node id="inner"/>\n    </node>')
    ctx = run(doc)
    assert 'composite-children' in errors(ctx)


def test_unknown_tag_rejected():
    """Check unknown tag rejected."""
    doc = minimal().replace(b'</graphml>', b'<foo/>\n</graphml>')
    ctx = run(doc)
    assert 'tag-tree' in errors(ctx)


def test_key_on_wrong_element_kind_rejected():
    """Check key on wrong element kind rejected."""
    # dVertex on a graph
    doc = minimal().replace(
        b'    <data key="dStateMachine"/>',
        b'    <data key="dStateMachine"/>\n'
        b'    <data key="dVertex">initial</data>')
    assert 'key-usage' in errors(run(doc))
    # dRegion on a node
    doc = minimal().replace(
        b'      <data key="dName">Idle</data>',
        b'      <data key="dName">Idle</data>\n      <data key="dRegion"/>')
    assert 'key-usage' in errors(run(doc))
    # dPivot on a node
    doc = minimal().replace(
        b'      <data key="dName">Idle</data>',
        b'      <data key="dName">Idle</data>\n'
        b'      <data key="dPivot">dName</data>')
    assert 'key-usage' in errors(run(doc))


def test_wrong_geometry_subtag_rejected():
    """Check wrong geometry subtag rejected."""
    doc = minimal().replace(
        b'<edge id="init-n0#1" source="init" target="n0"/>',
        b'<edge id="init-n0#1" source="init" target="n0">\n'
        b'      <data key="dSourcePoint">'
        b'<rect x="0" y="0" width="1" height="1"/></data>\n'
        b'    </edge>')
    ctx = run(doc)
    assert 'tag-tree' in errors(ctx)


def test_incomplete_geometry_attributes_rejected():
    """Check incomplete geometry attributes rejected."""
    # rect without width
    doc = minimal().replace(
        b'      <data key="dName">Idle</data>',
        b'      <data key="dName">Idle</data>\n'
        b'      <data key="dGeometry"><rect x="0" y="0" height="10"/></data>')
    assert 'geometry-shape' in errors(run(doc))
    # point without y
    doc = minimal().replace(
        b'      <data key="dVertex">initial</data>',
        b'      <data key="dVertex">initial</data>\n'
        b'      <data key="dGeometry"><point x="0"/></data>')
    assert 'geometry-shape' in errors(run(doc))


def test_non_numeric_geometry_rejected():
    """Check non numeric geometry rejected."""
    doc = minimal().replace(
        b'      <data key="dName">Idle</data>',
        b'      <data key="dName">Idle</data>\n'
        b'      <data key="dGeometry">'
        b'<rect x="a" y="0" width="1" height="1"/></data>')
    ctx = run(doc)
    assert 'geometry-shape' in errors(ctx)


def test_l2_errors_stop_the_pipeline():
    """Check L2 errors stop the pipeline."""
    ctx = run(minimal(gformat=''))
    assert ctx.report.layers_run == [1, 2]
    assert ctx.report.verdict() == 'invalid'
