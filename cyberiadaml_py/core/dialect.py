# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The Lapki dialect pass: repairs between L1 and L2 (informative)
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
"""The Lapki dialect pass: repairs between L1 and L2 (informative)."""
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from . import meta
from .findings import WARNING
from .rules import declare

LAPKI = 'lapki'
DIALECTS = (LAPKI,)

FORMAT_VALUE = 'Cyberiada-GraphML-1.0'
FORMAT_LAPKI = 'Cyberiada-GraphML-Lapki'
OLD_FORMAT = 'Cyberiada-GraphML'
META_NAME = 'CGML_META'
COMPONENT_NAME = 'CGML_COMPONENT'
PRIVATE_PREFIX = 'dLapki'
LAPKI_HINT = 'lapkiVisual'
UNDEFINED = 'undefined'
POINT_KINDS = ('initial', 'final', 'terminate', 'shallowHistory',
               'deepHistory', 'entryPoint', 'exitPoint')
RECT_KINDS = ('state', 'submachine', 'comment', 'choice')
SIZE_OF_POINT = -1.0     # cyberiadaml-js 1.x stores a point as such a rect

declare('lapki-d1', 'LAPKI-D1', 0, WARNING,
        'one metadata node, at the top of the first state machine')
declare('lapki-d2', 'LAPKI-D2', 0, WARNING,
        'components named CGML_COMPONENT <id>, not linked to the metadata')
declare('lapki-d3', 'LAPKI-D3', 0, WARNING,
        'a region graph id differs from the node ids')
declare('lapki-d4a', 'LAPKI-D4', 0, WARNING,
        'a point node carries no -1 x -1 rect')
declare('lapki-d4b', 'LAPKI-D4', 0, WARNING,
        'a rect node carries no point')
declare('lapki-d5a', 'LAPKI-D5', 0, WARNING,
        'private Lapki keys are declared')
declare('lapki-d5b', 'LAPKI-D5', 0, WARNING,
        'private Lapki keys carry text, not a point')
declare('lapki-d6', 'LAPKI-D6', 0, WARNING,
        'gFormat is first and carries the version')
declare('lapki-d7a', 'LAPKI-D7', 0, WARNING,
        'edge ids are unique')
declare('lapki-d7b', 'LAPKI-D7', 0, WARNING,
        'dNote is the first data key of a comment')
declare('lapki-d7d', 'LAPKI-D7', 0, WARNING,
        'dNote is not empty')
declare('lapki-d7e', 'LAPKI-D7', 0, WARNING,
        'a state machine graph carries edgedefault')
declare('lapki-d7f', 'LAPKI-D7', 0, WARNING,
        'node ids are unique across the state machines')
declare('lapki-d8a', 'LAPKI-D8', 0, WARNING,
        'transitionOrder is actionFirst or exitFirst')
declare('lapki-d8b', 'LAPKI-D8', 0, WARNING,
        'a state machine has a name')
declare('lapki-d9', 'LAPKI-D9', 0, WARNING,
        'top-level graphs are state machines')

_SUFFIX = re.compile(r'^(.*)#(\d+)$')


@dataclass
class Result:
    """What the pass leaves for the reader besides the repaired tree."""

    dialect: str
    label: str = FORMAT_VALUE
    # state machine graph id -> the parameters of its removed metadata node
    machine_params: dict = field(default_factory=dict)
    extension_graphs: list = field(default_factory=list)
    # an id given by D-7f or D-7a -> the id as written
    renamed: dict = field(default_factory=dict)
    repairs: int = 0


def _datas(elem):
    return [child for child in elem if child.tag == 'data']


def _data(elem, key):
    for child in elem:
        if child.tag == 'data' and child.get('key') == key:
            return child
    return None


def _text(elem):
    return (elem.text or '') if elem is not None else ''


def _is_formal(node, name):
    note, title = _data(node, 'dNote'), _data(node, 'dName')
    return note is not None and title is not None and \
        _text(note).strip() == 'formal' and _text(title).strip() == name


def _serialize(params):
    return '\n\n'.join('%s/ %s' % (p.name, p.value) for p in params)


def _parents(root):
    return {child: parent for parent in root.iter() for child in parent}


def _format(ctx, root):
    found = [c for c in root if c.tag == 'data' and c.get('key') == 'gFormat']
    if not found:
        return
    elem = found[0]
    if _text(elem).strip() == OLD_FORMAT:
        ctx.emit('lapki-d6', 'gFormat %r without the version, read as %s' %
                 (OLD_FORMAT, FORMAT_VALUE), elem=elem)
        elem.text = FORMAT_VALUE
    if list(root).index(elem) != 0:
        ctx.emit('lapki-d6', 'gFormat is not the first child of graphml',
                 elem=elem)
        root.remove(elem)
        root.insert(0, elem)


def _private_keys(ctx, root):
    declared = {k.get('id') for k in root if k.tag == 'key'}
    missing = {}
    for owner in root.iter():
        if owner.tag not in ('graph', 'node', 'edge'):
            continue
        for data in _datas(owner):
            key = data.get('key') or ''
            if key.startswith(PRIVATE_PREFIX) and key not in declared:
                missing.setdefault((key, owner.tag), data)
    children = list(root)
    keys = [i for i, c in enumerate(children) if c.tag == 'key']
    pos = keys[-1] + 1 if keys else 1
    for (key, kind), data in missing.items():
        ctx.emit('lapki-d5a', 'private key %s for %s used without a '
                 'declaration' % (key, kind), elem=data)
        decl = ET.Element('key', {
            'id': key, 'for': kind,
            'attr.name': 'lapki' + key[len(PRIVATE_PREFIX):],
            'attr.type': 'string'})
        root.insert(pos, decl)
        ctx.parsed.inherit(decl, data)
        pos += 1


def _private_points(ctx, root):
    for data in root.iter('data'):
        key = data.get('key') or ''
        children = list(data)
        if not key.startswith(PRIVATE_PREFIX) or len(children) != 1 \
                or children[0].tag != 'point':
            continue
        point = children[0]
        ctx.emit('lapki-d5b', 'point inside the private key %s, kept as '
                 'text' % key, elem=data)
        data.remove(point)
        data.text = 'x/ %s\n\ny/ %s' % (point.get('x'), point.get('y'))


def _functions(ctx, root, result):
    for graph in [g for g in root if g.tag == 'graph']:
        keys = [d.get('key') for d in _datas(graph)]
        if 'dFunction' in keys and 'dStateMachine' not in keys:
            ctx.emit('lapki-d9', 'function graph %r is not a state machine' %
                     graph.get('id'), elem=graph)
            root.remove(graph)
            result.extension_graphs.append(graph)


def _region_ids(ctx, root):
    node_ids = {n.get('id') for n in root.iter('node')}
    taken = node_ids | {g.get('id') for g in root.iter('graph')} | \
        {e.get('id') for e in root.iter('edge')}
    for node in root.iter('node'):
        for graph in [g for g in node if g.tag == 'graph']:
            gid = graph.get('id')
            if gid is None or gid not in node_ids:
                continue
            base = '%s::region' % node.get('id')
            new, number = base, 2
            while new in taken:
                new = '%s-%d' % (base, number)
                number += 1
            ctx.emit('lapki-d3', 'region graph id %r equals a node id, read '
                     'as %r' % (gid, new), elem=graph)
            graph.set('id', new)
            taken.add(new)


def _node_ids(ctx, root, result):
    taken = {n.get('id') for n in root.iter('node')} | \
        {g.get('id') for g in root.iter('graph')}
    seen = set()
    for machine in [g for g in root if g.tag == 'graph']:
        nodes = list(machine.iter('node'))
        renamed = {}
        for node in nodes:
            nid = node.get('id')
            if nid is None or nid not in seen:
                continue
            base = '%s::%s' % (machine.get('id'), nid)
            new, number = base, 2
            while new in taken:
                new = '%s-%d' % (base, number)
                number += 1
            ctx.emit('lapki-d7f', 'node id %r repeats one of an earlier '
                     'state machine, read as %r' % (nid, new), elem=node)
            node.set('id', new)
            taken.add(new)
            renamed[nid] = new
            result.renamed[new] = nid
        for edge in machine.iter('edge'):
            for end in ('source', 'target'):
                if edge.get(end) in renamed:
                    edge.set(end, renamed[edge.get(end)])
        seen.update(n.get('id') for n in nodes)


def _edge_ids(ctx, root, result):
    edges = list(root.iter('edge'))
    taken = {e.get('id') for e in edges}
    seen = set()
    for edge in edges:
        eid = edge.get('id')
        if eid is None:
            continue
        if eid in seen:
            match = _SUFFIX.match(eid)
            base = match.group(1) if match else eid
            number = 1
            while '%s#%d' % (base, number) in taken:
                number += 1
            new = '%s#%d' % (base, number)
            ctx.emit('lapki-d7a', 'duplicate edge id %r, read as %r' %
                     (eid, new), elem=edge)
            edge.set('id', new)
            taken.add(new)
            result.renamed[new] = eid
            eid = new
        seen.add(eid)


def _rewrite_meta(ctx, node):
    data = _data(node, 'dData')
    params, errors = meta.parse(_text(data) if data is not None else '')
    if errors:
        return
    changed = False
    kept = []
    names = set()
    for param in params:
        value = param.value.strip()
        if param.name in names:
            ctx.emit('lapki-d1', 'metadata parameter %s repeated, the first '
                     'occurrence kept' % param.name, elem=node)
            changed = True
            continue
        names.add(param.name)
        if value == UNDEFINED:
            ctx.emit('lapki-d1', 'metadata parameter %s/ %s dropped' %
                     (param.name, UNDEFINED), elem=node)
            changed = True
            continue
        if param.name == 'transitionOrder' and value == 'transitionFirst':
            ctx.emit('lapki-d8a', 'transitionOrder/ transitionFirst read as '
                     'actionFirst', elem=node)
            param.value = 'actionFirst'
            changed = True
        kept.append(param)
    version = [p for p in kept if p.name == 'standardVersion']
    if not version or not version[0].value.strip():
        ctx.emit('lapki-d1', 'metadata without a standardVersion value, 1.0 '
                 'assumed', elem=node)
        kept = [p for p in kept if p.name != 'standardVersion']
        kept.insert(0, meta.Param('standardVersion', '1.0', 0))
        changed = True
    if not changed:
        return
    if data is None:
        data = ET.SubElement(node, 'data', {'key': 'dData'})
        ctx.parsed.inherit(data, node)
    data.text = _serialize(kept)


def _meta(ctx, root, result):
    machines = [g for g in root if g.tag == 'graph']
    parents = _parents(root)
    metas = []
    for index, machine in enumerate(machines):
        for node in machine.iter('node'):
            if _is_formal(node, META_NAME):
                metas.append((index, machine, node))
    for _, machine, node in metas:
        params, _ = meta.parse(_text(_data(node, 'dData')))
        if any(p.name == LAPKI_HINT for p in params):
            result.label = FORMAT_LAPKI
    # the older component attachment: edges from a metadata node, which
    # may sit in another machine
    meta_ids = {node.get('id') for _, _, node in metas}
    for machine in machines:
        for edge in [e for e in machine if e.tag == 'edge']:
            if edge.get('source') in meta_ids:
                ctx.emit('lapki-d2', 'edge %r links the metadata to %r' %
                         (edge.get('id'), edge.get('target')), elem=edge)
                machine.remove(edge)
    if not metas:
        return
    top = [m for m in metas if m[0] == 0 and parents[m[2]] is machines[0]]
    kept = top[0] if top else metas[0]
    for item in metas:
        if item is kept:
            continue
        _, machine, node = item
        params, _ = meta.parse(_text(_data(node, 'dData')))
        result.machine_params[machine.get('id')] = \
            [p for p in params if p.value.strip() != UNDEFINED]
        ctx.emit('lapki-d1', 'metadata node %r in the state machine %r, its '
                 'parameters kept for that machine' %
                 (node.get('id'), machine.get('id')), elem=node)
        parents[node].remove(node)
        for edge in [e for e in machine if e.tag == 'edge']:
            if node.get('id') in (edge.get('source'), edge.get('target')):
                machine.remove(edge)
    node = kept[2]
    if parents[node] is not machines[0]:
        ctx.emit('lapki-d1', 'metadata node %r moved to the first state '
                 'machine' % node.get('id'), elem=node)
        parents[node].remove(node)
        first = machines[0]
        position = len(_datas(first))
        first.insert(position, node)
    _rewrite_meta(ctx, node)


def _components(ctx, root):
    for node in root.iter('node'):
        if not _is_formal(node, COMPONENT_NAME):
            continue
        data = _data(node, 'dData')
        params, errors = meta.parse(_text(data))
        ids = [p for p in params if p.name == 'id']
        if errors or not ids:
            continue
        cid = ids[0].value.strip()
        ctx.emit('lapki-d2', 'component comment %r named %s with the id in '
                 'its body' % (node.get('id'), COMPONENT_NAME), elem=node)
        _data(node, 'dName').text = '%s %s' % (COMPONENT_NAME, cid)
        data.text = _serialize([p for p in params if p.name != 'id'])


def _node_kind(keys, node):
    if 'dNote' in keys:
        return 'comment'
    if 'dVertex' in keys:
        return _text(_data(node, 'dVertex')).strip()
    if 'dSubmachineState' in keys:
        return 'submachine'
    return 'state'


def _number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _geometry(ctx, node, kind):
    geometry = _data(node, 'dGeometry')
    shapes = list(geometry) if geometry is not None else []
    if len(shapes) != 1:
        return
    shape = shapes[0]
    if kind in POINT_KINDS and shape.tag == 'rect' and \
            _number(shape.get('width')) == SIZE_OF_POINT and \
            _number(shape.get('height')) == SIZE_OF_POINT:
        ctx.emit('lapki-d4a', '-1 x -1 rect on the %s node %r, read as a '
                 'point' % (kind, node.get('id')), elem=shape)
        point = ET.Element('point', {'x': shape.get('x'),
                                     'y': shape.get('y')})
        geometry.remove(shape)
        geometry.append(point)
        ctx.parsed.inherit(point, shape)
    elif kind in RECT_KINDS and shape.tag == 'point':
        ctx.emit('lapki-d4b', 'point on the %s node %r, read as a loose '
                 'rect' % (kind, node.get('id')), elem=shape)
        rect = ET.Element('rect', {'x': shape.get('x'), 'y': shape.get('y'),
                                   'width': '0', 'height': '0'})
        geometry.remove(shape)
        geometry.append(rect)
        ctx.parsed.inherit(rect, shape)


def _nodes(ctx, root):
    for node in root.iter('node'):
        datas = _datas(node)
        keys = [d.get('key') for d in datas]
        note = _data(node, 'dNote')
        if note is not None and not _text(note).strip():
            ctx.emit('lapki-d7d', 'empty dNote on %r, read as informal' %
                     node.get('id'), elem=note)
            note.text = 'informal'
        if note is not None and keys[0] != 'dNote':
            ctx.emit('lapki-d7b', 'dNote is not the first data key of %r' %
                     node.get('id'), elem=note)
            node.remove(note)
            node.insert(0, note)
        _geometry(ctx, node, _node_kind(keys, node))


def _machines(ctx, root):
    for graph in [g for g in root if g.tag == 'graph']:
        if graph.get('edgedefault') is None:
            ctx.emit('lapki-d7e', 'state machine graph %r without '
                     'edgedefault, read as directed' % graph.get('id'),
                     elem=graph)
            graph.set('edgedefault', 'directed')
        name = _data(graph, 'dName')
        if name is not None and _text(name).strip():
            continue
        ctx.emit('lapki-d8b', 'state machine %r without a name, named by '
                 'its id' % graph.get('id'), elem=graph)
        if name is None:
            name = ET.Element('data', {'key': 'dName'})
            marker = _data(graph, 'dStateMachine')
            position = list(graph).index(marker) + 1 if marker is not None \
                else 0
            graph.insert(position, name)
            ctx.parsed.inherit(name, graph)
        name.text = graph.get('id')


def apply(ctx, dialect=LAPKI):
    """Repair the parsed tree of ctx in place; return the Result."""
    if dialect not in DIALECTS:
        raise ValueError('unknown dialect: %s' % dialect)
    result = Result(dialect)
    root = ctx.parsed.root
    if root.tag != 'graphml':
        return result
    before = len(ctx.report.findings)
    _format(ctx, root)
    _private_keys(ctx, root)
    _private_points(ctx, root)
    _functions(ctx, root, result)
    _meta(ctx, root, result)
    _components(ctx, root)
    _node_ids(ctx, root, result)
    _region_ids(ctx, root)
    _edge_ids(ctx, root, result)
    _nodes(ctx, root)
    _machines(ctx, root)
    result.repairs = len(ctx.report.findings) - before
    if result.repairs:
        result.label = FORMAT_LAPKI
    return result
