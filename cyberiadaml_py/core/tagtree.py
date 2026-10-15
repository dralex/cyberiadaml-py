# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The L2 layer: the admissible tag tree of the testing specification 2.8.1
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
"""The L2 layer: the admissible tag tree of the testing specification 2.8.1."""
from .findings import ERROR, INFO, WARNING
from .keys import STANDARD_KEY_IDS
from .rules import declare

GRAPHML_NS = 'http://graphml.graphdrawing.org/xmlns'

declare('root-graphml', 'CGML-5.1-2', 2, ERROR,
        'the root tag is graphml with the GraphML namespace')
declare('extra-namespaces', 'CGML-5.1-3', 2, INFO,
        'additional namespace attributes are tolerated')
declare('gformat-first', 'CGML-5.4-1', 2, ERROR,
        'the gFormat data tag is the first child of graphml')
declare('key-placement', 'CGML-5.5-1', 2, ERROR,
        'key declarations precede the graph structure')
declare('graph-in-graph', 'CGML-5.6-3', 2, ERROR,
        'subgraphs nest only inside nodes', also=('CGML-6.1-6',))
declare('graph-child-order', 'CGML-5.6-3', 2, ERROR,
        'graph children are ordered keys, nodes, edges')
declare('node-placement', 'CGML-5.7-2', 2, ERROR,
        'nodes appear only inside graphs')
declare('node-content', 'CGML-5.7-3', 2, INFO,
        'nodes contain data keys and nested graphs',
        note='admissible content is accepted by the walker')
declare('edge-block', 'CGML-5.8-3', 2, WARNING,
        'edges form a single block at the end of the graph')
declare('sm-first-key', 'CGML-6.1-1', 2, ERROR,
        'dStateMachine is the first key of a state machine graph')
declare('sm-child-order', 'CGML-6.1-4', 2, ERROR,
        'state machine children are ordered keys, nodes, edges')
declare('node-marker', 'CGML-5.7-4', 2, ERROR,
        'a node carries at most one marker key')
declare('vertex-first-key', 'CGML-6.4-1', 2, ERROR,
        'dVertex is the first key of a vertex node')
declare('submachine-first-key', 'CGML-8.1-1', 2, ERROR,
        'dSubmachineState is the first key of a submachine state node')
declare('submachine-subgraph', 'CGML-8.1-2', 2, ERROR,
        'a submachine subgraph holds entry/exit points only, without keys')
declare('submachine-no-data', 'CGML-8.1-3', 2, ERROR,
        'a submachine state carries no dData')
declare('region-marker-required', 'CGML-6.5-5', 2, ERROR,
        'each of two or more regions starts with the dRegion key')
declare('composite-children', 'CGML-6.5-1', 2, ERROR,
        'composite state children live in region subgraphs')
declare('region-no-edges', 'CGML-6.5-8', 2, ERROR,
        'child transitions are placed at the top level, not in regions')
declare('note-first-key', 'CGML-6.6-1', 2, ERROR,
        'dNote is the first key of a comment node')
declare('pivot-first-key', 'CGML-6.7-1', 2, ERROR,
        'dPivot is the first key of a comment link edge')
declare('geometry-shape', 'CGML-7.2-2', 2, ERROR,
        'rect and point tags carry their numeric attributes')
declare('tag-tree', 'CGML-appendix-A-1', 2, ERROR,
        'tag placement follows the admissible tag tree')
declare('key-usage', 'CGML-appendix-A-1', 2, ERROR,
        'data keys appear on their admissible element kinds',
        also=('CGML-9.2-4',))

GRAPH_KEYS = ('dStateMachine', 'dName', 'dGeometry', 'dFormalName')
REGION_KEYS = ('dRegion', 'dName', 'dGeometry', 'dFormalName')
NODE_KEYS = ('dNote', 'dSubmachineState', 'dVertex', 'dName', 'dGeometry',
             'dData', 'dFormalName', 'dCollapsed', 'dColor', 'dMarkup')
EDGE_KEYS = ('dPivot', 'dChunk', 'dData', 'dLabelGeometry', 'dGeometry',
             'dSourcePoint', 'dTargetPoint', 'dColor')

# (carrier kind, key) -> (admissible sub-tags, min count, max count)
GEOMETRY_CONTENT = {
    ('graph', 'dGeometry'): (('rect',), 1, 1),
    ('node', 'dGeometry'): (('point', 'rect'), 1, 1),
    ('edge', 'dGeometry'): (('point',), 1, None),
    ('edge', 'dLabelGeometry'): (('point', 'rect'), 1, 1),
    ('edge', 'dSourcePoint'): (('point',), 1, 1),
    ('edge', 'dTargetPoint'): (('point',), 1, 1),
}

MARKER_KEYS = ('dNote', 'dVertex', 'dSubmachineState')
ENTRY_EXIT = ('entryPoint', 'exitPoint')
RECT_ATTRS = ('x', 'y', 'width', 'height')
POINT_ATTRS = ('x', 'y')


def _is_number(value):
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _check_geometry_element(ctx, elem):
    attrs = RECT_ATTRS if elem.tag == 'rect' else POINT_ATTRS
    for name in attrs:
        value = elem.get(name)
        if value is None:
            ctx.emit('geometry-shape',
                     '%s tag misses the %s attribute' % (elem.tag, name),
                     elem=elem)
        elif not _is_number(value):
            ctx.emit('geometry-shape',
                     '%s attribute %s is not a number: %r' %
                     (elem.tag, name, value), elem=elem)


def _check_data_content(ctx, kind, data):
    """Check the sub-tags of one data element of a graph/node/edge."""
    key = data.get('key')
    content = GEOMETRY_CONTENT.get((kind, key))
    if content is None:
        for child in data:
            ctx.emit('tag-tree',
                     'tag %s is not admissible inside data key %s' %
                     (child.tag, key), elem=child)
        return
    tags, low, high = content
    count = 0
    for child in data:
        if child.tag not in tags:
            ctx.emit('tag-tree',
                     'tag %s is not admissible inside data key %s '
                     '(expected %s)' % (child.tag, key, ' or '.join(tags)),
                     elem=child)
            continue
        count += 1
        _check_geometry_element(ctx, child)
    if count < low or (high is not None and count > high):
        ctx.emit('geometry-shape',
                 'data key %s must contain %s %s tag(s), found %d' %
                 (key, low if high == low else 'at least %d' % low,
                  ' or '.join(tags), count), elem=data)


def _first_key_check(ctx, rule_name, marker, datas):
    """Check that the marker key, when present, is the first data key."""
    keys = [d.get('key') for d in datas]
    if marker in keys and keys[0] != marker:
        ctx.emit(rule_name,
                 '%s is not the first data key (found after %s)' %
                 (marker, keys[0]), elem=datas[0])


def _check_edge(ctx, edge):
    datas = []
    for child in edge:
        if child.tag == 'data':
            datas.append(child)
            key = child.get('key')
            if key in STANDARD_KEY_IDS and key not in EDGE_KEYS:
                ctx.emit('key-usage',
                         'data key %s is not admissible on an edge' % key,
                         elem=child)
            _check_data_content(ctx, 'edge', child)
        else:
            ctx.emit('tag-tree',
                     'tag %s is not admissible inside an edge' % child.tag,
                     elem=child)
    if datas:
        _first_key_check(ctx, 'pivot-first-key', 'dPivot', datas)


def _check_submachine_subgraph(ctx, graph):
    """8.1-2: no data keys, only entry/exit point vertex nodes."""
    for child in graph:
        if child.tag == 'data':
            ctx.emit('submachine-subgraph',
                     'data key %s inside a submachine subgraph' %
                     child.get('key'), elem=child)
        elif child.tag == 'node':
            keys = [(d.get('key'), (d.text or '').strip())
                    for d in child if d.tag == 'data']
            if not keys or keys[0][0] != 'dVertex' \
                    or keys[0][1] not in ENTRY_EXIT:
                ctx.emit('submachine-subgraph',
                         'node %r inside a submachine subgraph is not an '
                         'entry or exit point' % child.get('id'), elem=child)


def _check_node(ctx, node):
    datas = []
    graphs = []
    seen_graph = False
    for child in node:
        if child.tag == 'data':
            if seen_graph:
                ctx.emit('tag-tree',
                         'data key after a region subgraph inside a node',
                         elem=child)
            datas.append(child)
            key = child.get('key')
            if key in STANDARD_KEY_IDS and key not in NODE_KEYS:
                ctx.emit('key-usage',
                         'data key %s is not admissible on a node' % key,
                         elem=child)
            _check_data_content(ctx, 'node', child)
        elif child.tag == 'graph':
            seen_graph = True
            graphs.append(child)
            _check_graph(ctx, child, 'region')
        elif child.tag == 'node':
            ctx.emit('composite-children',
                     'node nested directly inside a node; children live in '
                     'region subgraphs', elem=child)
        else:
            ctx.emit('tag-tree',
                     'tag %s is not admissible inside a node' % child.tag,
                     elem=child)
    keys = [d.get('key') for d in datas]
    markers = [k for k in keys if k in MARKER_KEYS]
    if len(markers) > 1:
        ctx.emit('node-marker',
                 'node carries the marker keys %s' % ' and '.join(markers),
                 elem=datas[keys.index(markers[1])])
    if datas:
        _first_key_check(ctx, 'vertex-first-key', 'dVertex', datas)
        _first_key_check(ctx, 'note-first-key', 'dNote', datas)
        _first_key_check(ctx, 'submachine-first-key', 'dSubmachineState',
                         datas)
    if 'dSubmachineState' in keys:
        if 'dData' in keys:
            ctx.emit('submachine-no-data',
                     'submachine state carries a dData key',
                     elem=datas[keys.index('dData')])
        if len(graphs) > 1:
            ctx.emit('submachine-subgraph',
                     'submachine state with %d subgraphs; at most one '
                     'holds the entry/exit points' % len(graphs),
                     elem=graphs[1])
        for graph in graphs:
            _check_submachine_subgraph(ctx, graph)
    elif len(graphs) > 1:
        for graph in graphs:
            first = [d.get('key') for d in graph if d.tag == 'data'][:1]
            if first != ['dRegion']:
                ctx.emit('region-marker-required',
                         'region %r of a state with %d regions does not '
                         'start with the dRegion key' %
                         (graph.get('id'), len(graphs)), elem=graph)


def _check_graph(ctx, graph, kind):
    """Walk one graph: kind is 'sm' (top level) or 'region' (inside a node)."""
    allowed = GRAPH_KEYS if kind == 'sm' else REGION_KEYS
    order_rule = 'sm-child-order' if kind == 'sm' else 'graph-child-order'
    datas = []
    phase = 'data'
    for child in graph:
        if child.tag == 'data':
            if phase != 'data':
                ctx.emit(order_rule,
                         'data key after the first node of the graph',
                         elem=child)
            else:
                datas.append(child)
            key = child.get('key')
            if key in STANDARD_KEY_IDS and key not in allowed:
                ctx.emit('key-usage',
                         'data key %s is not admissible on a %s graph' %
                         (key, 'state machine' if kind == 'sm' else 'region'),
                         elem=child)
            _check_data_content(ctx, 'graph', child)
        elif child.tag == 'node':
            if phase == 'edge':
                ctx.emit('edge-block',
                         'node after an edge; edges must form a single '
                         'trailing block', elem=child)
            phase = 'node' if phase == 'data' else phase
            _check_node(ctx, child)
        elif child.tag == 'edge':
            if kind == 'region':
                ctx.emit('region-no-edges',
                         'edge inside a region subgraph', elem=child)
            phase = 'edge'
            _check_edge(ctx, child)
        elif child.tag == 'graph':
            ctx.emit('graph-in-graph',
                     'subgraph directly inside a graph; subgraphs nest only '
                     'inside nodes', elem=child)
        elif child.tag == 'key':
            ctx.emit('key-placement',
                     'key declaration inside a graph', elem=child)
        else:
            ctx.emit('tag-tree',
                     'tag %s is not admissible inside a graph' % child.tag,
                     elem=child)
    if kind == 'sm' and datas:
        keys = [d.get('key') for d in datas]
        if keys and keys[0] != 'dStateMachine' and 'dStateMachine' in keys:
            ctx.emit('sm-first-key',
                     'dStateMachine is not the first key of the state '
                     'machine graph', elem=datas[0])


def _check_root(ctx, root):
    if root.tag != 'graphml':
        ctx.emit('root-graphml',
                 'the root tag is %s, not graphml' % root.tag, elem=root)
        return False
    xmlns = root.get('xmlns')
    if xmlns is None:
        ctx.emit('root-graphml', 'the graphml tag has no xmlns attribute',
                 elem=root)
    elif xmlns != GRAPHML_NS:
        ctx.emit('root-graphml',
                 'the graphml namespace is %s, expected %s' %
                 (xmlns, GRAPHML_NS), elem=root)
    for name in root.keys():
        if name.startswith('xmlns:'):
            ctx.emit('extra-namespaces',
                     'additional namespace attribute %s' % name, elem=root)
    return True


def check(ctx):
    """Run the L2 tag tree walk over the parsed document."""
    root = ctx.parsed.root
    if not _check_root(ctx, root):
        return
    # graphml children: data<gFormat>, key*, graph*
    phase = 'gformat'
    saw_gformat = False
    for index, child in enumerate(root):
        if child.tag == 'data':
            key = child.get('key')
            if key != 'gFormat':
                if key in STANDARD_KEY_IDS:
                    ctx.emit('key-usage',
                             'data key %s is not admissible on graphml '
                             '(only gFormat)' % key, elem=child)
            else:
                saw_gformat = True
                if index > 0:
                    ctx.emit('gformat-first',
                             'the gFormat data tag is not the first child '
                             'of graphml', elem=child)
            phase = 'keys' if phase == 'gformat' else phase
        elif child.tag == 'key':
            if phase == 'graphs':
                ctx.emit('key-placement',
                         'key declaration after the graph structure',
                         elem=child)
            else:
                phase = 'keys'
        elif child.tag == 'graph':
            phase = 'graphs'
            _check_graph(ctx, child, 'sm')
        elif child.tag == 'node':
            ctx.emit('node-placement',
                     'node directly inside graphml; nodes appear only '
                     'inside graphs', elem=child)
        else:
            ctx.emit('tag-tree',
                     'tag %s is not admissible inside graphml' % child.tag,
                     elem=child)
    if not saw_gformat:
        ctx.emit('gformat-first', 'the gFormat data tag is missing',
                 elem=root)
