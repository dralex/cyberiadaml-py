# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The L4 layer: document integrity checks
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
"""The L4 layer: document integrity checks."""
from . import model as model_mod
from .findings import ERROR, INFO, WARNING
from .model import (Comment, Point, Rect, State, SubmachineState,
                    Vertex, data_items, iter_elements)
from .rules import declare, rule

declare('geometry-mode-detect', 'CGML-7.1-1', 4, INFO,
        'the document geometry mode is resolved from the metadata',
        note='resolved by the model')
declare('sm-geometry', 'CGML-7.2-1-1', 2, INFO,
        'state machine geometry is a rect',
        note='shape constrained by the tag tree')
declare('region-geometry', 'CGML-7.2-1-4', 2, INFO,
        'region geometry is a rect',
        note='shape constrained by the tag tree')
declare('label-geometry', 'CGML-7.2-1-6', 2, INFO,
        'transition label geometry is a point or a rect',
        note='shape constrained by the tag tree')


def _machine_index(machine):
    """Return the node/edge id sets of one state machine."""
    node_ids = set()
    comment_ids = set()
    for node in _machine_nodes(machine):
        if node.id is not None:
            node_ids.add(node.id)
            if isinstance(node, Comment):
                comment_ids.add(node.id)
    edge_ids = {t.id for t in machine.transitions if t.id is not None}
    edge_ids |= {link.id for link in machine.links if link.id is not None}
    return node_ids, comment_ids, edge_ids


def _machine_nodes(machine):
    def walk(children):
        for child in children:
            yield child
            for region in getattr(child, 'regions', ()):
                yield from walk(region.children)
    yield from walk(machine.children)


def _levels(document):
    """All sibling levels: (container description, children list)."""
    for machine in document.machines:
        yield 'state machine %r' % machine.id, machine.children
    for region in model_mod.iter_regions(document):
        yield 'region %r' % region.id, region.children


@rule('top-level-graphs', 'CGML-5.6-2', 4, ERROR,
      'the document contains at least one state machine graph')
def _top_level_graphs(ctx):
    if not ctx.model.machines:
        ctx.emit('top-level-graphs',
                 'the document contains no top-level graphs',
                 elem=ctx.model.root)


@rule('unique-ids', 'CGML-5.9-4', 4, ERROR,
      'ids are unique across the whole document', also=('CGML-5.7-1',))
def _unique_ids(ctx):
    seen = {}
    for kind, elem in iter_elements(ctx.model.root):
        value = elem.get('id')
        if not value:
            continue
        if value in seen:
            ctx.emit('unique-ids',
                     '%s id %r duplicates the id of a %s' %
                     (kind, value, seen[value]), elem=elem)
        else:
            seen[value] = kind


@rule('unique-data-keys', 'CGML-5.5-4', 4, ERROR,
      'a tag carries at most one data of each key')
def _unique_data_keys(ctx):
    for kind, elem in iter_elements(ctx.model.root):
        seen = set()
        for key, data in data_items(elem):
            if key is None:
                continue
            if key in seen:
                ctx.emit('unique-data-keys',
                         '%s carries more than one data with the key %s' %
                         (kind, key), elem=data)
            seen.add(key)


@rule('sm-marker', 'CGML-6.1-1', 4, ERROR,
      'every top-level graph carries the dStateMachine marker')
def _sm_marker(ctx):
    for machine in ctx.model.machines:
        if not machine.marker:
            ctx.emit('sm-marker',
                     'top-level graph without the dStateMachine key',
                     elem=machine.elem)


@rule('sm-name', 'CGML-6.1-2', 4, ERROR,
      'state machines carry unique non-empty names')
def _sm_name(ctx):
    seen = {}
    for machine in ctx.model.machines:
        if machine.name is None:
            ctx.emit('sm-name', 'state machine without a dName key',
                     elem=machine.elem)
            continue
        name = machine.name.strip()
        if not name:
            ctx.emit('sm-name', 'state machine with an empty name',
                     elem=machine.elem)
        elif name in seen:
            ctx.emit('sm-name',
                     'state machines %r and %r share the name %r' %
                     (seen[name], machine.id, name), elem=machine.elem)
        else:
            seen[name] = machine.id


@rule('state-names', 'CGML-6.2-3', 4, ERROR,
      'sibling states carry unique names')
def _state_names(ctx):
    for where, children in _levels(ctx.model):
        seen = {}
        for child in children:
            if not isinstance(child, (State, SubmachineState)):
                continue
            name = (child.name or '').strip()
            if not name:
                continue
            if name in seen:
                ctx.emit('state-names',
                         'sibling states %r and %r in %s share the name %r' %
                         (seen[name], child.id, where, name), elem=child.elem)
            else:
                seen[name] = child.id


@rule('formal-name-unique', 'CGML-10.1-3', 4, ERROR,
      'formal names are unique among state machines and among siblings')
def _formal_name_unique(ctx):
    seen = {}
    for machine in ctx.model.machines:
        name = machine.formal_name
        if not name:
            continue
        if name in seen:
            ctx.emit('formal-name-unique',
                     'state machines %r and %r share the formal name %r' %
                     (seen[name], machine.id, name), elem=machine.elem)
        else:
            seen[name] = machine.id
    for where, children in _levels(ctx.model):
        level_seen = {}
        for child in children:
            name = getattr(child, 'formal_name', None)
            if not name or isinstance(child, Comment):
                continue
            if name in level_seen:
                ctx.emit('formal-name-unique',
                         'siblings %r and %r in %s share the formal name %r' %
                         (level_seen[name], child.id, where, name),
                         elem=child.elem)
            else:
                level_seen[name] = child.id


@rule('transition-endpoints', 'CGML-6.3-2', 4, ERROR,
      'transition endpoints resolve to nodes of the same state machine')
def _transition_endpoints(ctx):
    for machine in ctx.model.machines:
        node_ids, _, edge_ids = _machine_index(machine)
        for transition in machine.transitions:
            for attr in ('source', 'target'):
                value = getattr(transition, attr)
                if not value:
                    continue
                if value == machine.id:
                    ctx.emit('transition-endpoints',
                             'transition %s %r is the state machine graph '
                             'itself' % (attr, value), elem=transition.elem)
                elif value in edge_ids:
                    ctx.emit('link-target',
                             'plain transition %s %r is an edge id; only '
                             'comment links may target transitions' %
                             (attr, value), elem=transition.elem)
                elif value not in node_ids:
                    ctx.emit('transition-endpoints',
                             'transition %s %r does not name a node of '
                             'this state machine' % (attr, value),
                             elem=transition.elem)


declare('link-target', 'CGML-8.5-3', 4, ERROR,
        'only comment links may target an edge id')


@rule('link-endpoints', 'CGML-6.7-2', 4, ERROR,
      'comment link endpoints resolve within the same state machine')
def _link_endpoints(ctx):
    for machine in ctx.model.machines:
        node_ids, comment_ids, edge_ids = _machine_index(machine)
        for link in machine.links:
            source = link.source
            if source and source not in node_ids:
                ctx.emit('link-endpoints',
                         'comment link source %r does not name a node of '
                         'this state machine' % source, elem=link.elem)
            elif source and source not in comment_ids:
                ctx.emit('link-source',
                         'comment link source %r is not a comment node' %
                         source, elem=link.elem)
            if source and source == link.target:
                ctx.emit('link-source',
                         'comment link %r is a self-loop' % link.id,
                         elem=link.elem)
            target = link.target
            if target and target not in node_ids and target not in edge_ids:
                ctx.emit('link-endpoints',
                         'comment link target %r does not name a node or '
                         'an edge of this state machine' % target,
                         elem=link.elem)


declare('link-source', 'CGML-6.7-4', 4, ERROR,
        'a comment link leaves a comment node and is not a self-loop')


@rule('link-target-kind', 'CGML-8.5-2', 4, ERROR,
      'a comment link targeting an edge targets a transition')
def _link_target_kind(ctx):
    for machine in ctx.model.machines:
        link_ids = {link.id for link in machine.links
                    if link.id is not None}
        for link in machine.links:
            if link.target in link_ids:
                ctx.emit('link-target-kind',
                         'comment link target %r is a comment link, not a '
                         'transition' % link.target, elem=link.elem)


@rule('single-else', 'CGML-6.3-4', 4, ERROR,
      'at most one else transition leaves a node')
def _single_else(ctx):
    for machine in ctx.model.machines:
        vertices = {n.id: n for n in _machine_nodes(machine)
                    if isinstance(n, Vertex)}
        counts = {}
        for transition in machine.transitions:
            if any(b.guard == 'else' for b in transition.blocks):
                counts.setdefault(transition.source, []).append(transition)
        for source, transitions in counts.items():
            if len(transitions) < 2:
                continue
            vertex = vertices.get(source)
            if vertex is not None and vertex.kind == 'choice':
                ctx.emit('choice-single-else',
                         'choice %r has %d outgoing else transitions' %
                         (source, len(transitions)),
                         elem=transitions[1].elem)
            else:
                ctx.emit('single-else',
                         'node %r has %d outgoing else transitions' %
                         (source, len(transitions)),
                         elem=transitions[1].elem)


declare('choice-single-else', 'CGML-6.3-4', 4, ERROR,
        'at most one else transition leaves a choice')


@rule('single-initial', 'CGML-6.4-4-1', 4, ERROR,
      'at most one initial pseudostate per hierarchy level')
def _single_initial(ctx):
    for where, children in _levels(ctx.model):
        initials = [c for c in children
                    if isinstance(c, Vertex) and c.kind == 'initial']
        if len(initials) > 1:
            ctx.emit('single-initial',
                     '%s carries %d initial pseudostates' %
                     (where, len(initials)), elem=initials[1].elem)


@rule('meta-presence', 'CGML-6.9-1', 4, ERROR,
      'the first state machine carries the CGML_META formal comment')
def _meta_presence(ctx):
    doc = ctx.model
    if doc.machines and doc.meta_comment is None:
        ctx.emit('meta-presence',
                 'no CGML_META formal comment in the first state machine',
                 elem=doc.machines[0].elem)


@rule('meta-single', 'CGML-6.9-1', 4, ERROR,
      'the CGML_META comment is unique and is not linked')
def _meta_single(ctx):
    doc = ctx.model
    metas = [n for n in model_mod.iter_nodes(doc)
             if isinstance(n, Comment) and
             (n.kind or '').strip() == 'formal' and
             n.name == model_mod.META_NAME]
    for extra in metas[1:]:
        ctx.emit('meta-single', 'a second CGML_META comment %r' % extra.id,
                 elem=extra.elem)
    meta_ids = {m.id for m in metas if m.id is not None}
    for machine in doc.machines:
        for link in machine.links:
            if link.source in meta_ids or link.target in meta_ids:
                ctx.emit('meta-single',
                         'comment link %r attached to the CGML_META comment' %
                         link.id, elem=link.elem)


@rule('collapsed-needs-regions', 'CGML-8.4-2', 4, ERROR,
      'a collapsed state keeps its region subgraphs')
def _collapsed_needs_regions(ctx):
    for node in model_mod.iter_nodes(ctx.model):
        if isinstance(node, State) and node.collapsed and not node.regions:
            ctx.emit('collapsed-needs-regions',
                     'collapsed state %r has no region subgraph' % node.id,
                     elem=node.elem)


@rule('edge-geometry-mode', 'CGML-7.2-1-5', 4, WARNING,
      'transitions carry no geometry in the base (short) format')
def _edge_geometry_mode(ctx):
    doc = ctx.model
    if doc.geometry_mode == 'full':
        return
    for machine in doc.machines:
        for transition in machine.transitions:
            if transition.polyline or transition.source_point \
                    or transition.target_point:
                ctx.emit('edge-geometry-mode',
                         'transition geometry in a %r mode document' %
                         doc.geometry_mode, elem=transition.elem)


@rule('state-geometry-kind', 'CGML-7.2-1-2', 4, WARNING,
      'states, choices, comments and submachine states carry rect geometry')
def _state_geometry_kind(ctx):
    for node in model_mod.iter_nodes(ctx.model):
        rect_carrier = isinstance(node, (State, SubmachineState, Comment)) \
            or (isinstance(node, Vertex) and node.kind == 'choice')
        if rect_carrier and isinstance(node.geometry, Point):
            ctx.emit('state-geometry-kind',
                     'point geometry on %r, expected a rect' % node.id,
                     elem=node.elem)


@rule('vertex-geometry-kind', 'CGML-7.2-1-3', 4, WARNING,
      'pseudostates and final states carry point geometry')
def _vertex_geometry_kind(ctx):
    for node in model_mod.iter_nodes(ctx.model):
        if isinstance(node, Vertex) and node.kind != 'choice' \
                and isinstance(node.geometry, Rect):
            ctx.emit('vertex-geometry-kind',
                     'rect geometry on the %s vertex %r, expected a point' %
                     (node.kind, node.id), elem=node.elem)


@rule('transition-geometry-endpoints', 'CGML-6.3-5', 4, WARNING,
      'transition geometry requires geometry on both endpoint nodes')
def _transition_geometry_endpoints(ctx):
    for machine in ctx.model.machines:
        geometry = {n.id: n.geometry is not None
                    for n in _machine_nodes(machine)}
        for transition in machine.transitions:
            has_geometry = transition.label_geometry is not None \
                or transition.polyline or transition.source_point \
                or transition.target_point
            if not has_geometry:
                continue
            for endpoint in (transition.source, transition.target):
                if endpoint in geometry and not geometry[endpoint]:
                    ctx.emit('transition-geometry-endpoints',
                             'transition geometry while the endpoint node '
                             '%r has none' % endpoint, elem=transition.elem)
        # a link to a transition is drawn against the transition's source
        frames = {t.id: t.source for t in machine.transitions}
        for link in machine.links:
            if not (link.polyline or link.source_point or link.target_point):
                continue
            for endpoint in (link.source, frames.get(link.target, link.target)):
                if endpoint in geometry and not geometry[endpoint]:
                    ctx.emit('link-geometry-endpoints',
                             'comment link geometry while the node %r has '
                             'none' % endpoint, elem=link.elem)


declare('link-geometry-endpoints', 'CGML-6.7-6', 4, WARNING,
        'comment link geometry requires drawn ends: the comment and the '
        'subject node, or the source node of the commented transition')


@rule('link-geometry-ends', 'CGML-9.1-2', 4, WARNING,
      'a full-geometry document gives every comment link its ends')
def link_geometry_ends(ctx):
    if ctx.model.geometry_mode != 'full':
        return
    for machine in ctx.model.machines:
        for link in machine.links:
            if link.source_point is None:
                ctx.emit('link-geometry-ends',
                         'comment link %r has no source point' % link.id,
                         elem=link.elem)
            if link.target_point is None and \
                    (link.pivot or '').strip() not in ('dName', 'dData'):
                ctx.emit('link-geometry-ends',
                         'comment link %r to %r has no target point' %
                         (link.id, link.target), elem=link.elem)


ENTRY_EXIT = ('entryPoint', 'exitPoint')


def _is_point(node):
    return isinstance(node, Vertex) and node.kind in ENTRY_EXIT


@rule('initial-present', 'CGML-6.4-4-2', 4, INFO,
      'a state machine of a correct diagram contains an initial pseudostate')
def _initial_present(ctx):
    for machine in ctx.model.machines:
        if not any(isinstance(n, Vertex) and n.kind == 'initial'
                   for n in _machine_nodes(machine)):
            ctx.emit('initial-present',
                     'state machine %r contains no initial pseudostate' %
                     machine.id, elem=machine.elem)


def _aspect(target, pivot):
    """Return the commented text of a link target: name or dData."""
    if pivot == 'dName':
        return getattr(target, 'name', None)
    if isinstance(target, Comment):
        return target.body
    return getattr(target, 'data', None)


@rule('chunk-substring', 'CGML-6.7-3', 4, ERROR,
      'dChunk is a substring of the commented aspect of the subject')
def _chunk_substring(ctx):
    nodes = {n.id: n for n in model_mod.iter_nodes(ctx.model)}
    for machine in ctx.model.machines:
        edges = {t.id: t for t in machine.transitions}
        for link in machine.links:
            pivot = (link.pivot or '').strip()
            chunk = link.chunk or ''
            if pivot not in ('dName', 'dData') or not chunk.strip():
                continue
            target = nodes.get(link.target, edges.get(link.target))
            if target is None:
                continue
            if link.target in edges and pivot == 'dName':
                continue            # link-name-on-transition (8.5-4)
            aspect = _aspect(target, pivot)
            if aspect is None:
                ctx.emit('chunk-substring',
                         'the subject %r of the comment link %r has no %s '
                         'to comment' % (link.target, link.id, pivot),
                         elem=link.elem)
            elif chunk not in aspect:
                ctx.emit('chunk-substring',
                         'dChunk %r is not found in the %s of %r' %
                         (chunk, pivot, link.target), elem=link.elem)


@rule('link-name-on-transition', 'CGML-8.5-4', 4, ERROR,
      'a comment link to a transition comments its label, not a name')
def link_name_on_transition(ctx):
    for machine in ctx.model.machines:
        edges = {t.id for t in machine.transitions}
        for link in machine.links:
            if link.target in edges and (link.pivot or '').strip() == 'dName':
                ctx.emit('link-name-on-transition',
                         'comment link %r names a fragment of the transition '
                         '%r, which has no name' % (link.id, link.target),
                         elem=link.elem)


@rule('submachine-self-reference', 'CGML-8.1-1-1', 4, ERROR,
      'a submachine state does not reference its own state machine')
def _submachine_self_reference(ctx):
    for machine in ctx.model.machines:
        for node in _machine_nodes(machine):
            if isinstance(node, SubmachineState) and node.ref == machine.id:
                ctx.emit('submachine-self-reference',
                         'submachine state %r references its own state '
                         'machine %r' % (node.id, machine.id), elem=node.elem)


@rule('submachine-point-names', 'CGML-8.1-4', 4, ERROR,
      'the points of a submachine state are named after the points of the '
      'referenced state machine')
def _submachine_point_names(ctx):
    machines = {m.id: m for m in ctx.model.machines}
    for node in model_mod.iter_nodes(ctx.model):
        if not isinstance(node, SubmachineState) or node.ref not in machines:
            continue
        names = {(p.name or '').strip() for p in machines[node.ref].children
                 if _is_point(p)}
        for region in node.regions:
            for point in region.children:
                name = (point.name or '').strip()
                if _is_point(point) and name not in names:
                    ctx.emit('submachine-point-names',
                             'point %r of submachine state %r is named %r; '
                             'state machine %r defines the points %s' %
                             (point.id, node.id, point.name, node.ref,
                              sorted(names) or 'none'), elem=point.elem)


@rule('points-first-region', 'CGML-8.3-5', 4, ERROR,
      'the entry/exit points of a multi-region state sit in its first region')
def _points_first_region(ctx):
    for node in model_mod.iter_nodes(ctx.model):
        regions = getattr(node, 'regions', ())
        if isinstance(node, State) and len(regions) > 1:
            for region in regions[1:]:
                for point in region.children:
                    if _is_point(point):
                        ctx.emit('points-first-region',
                                 'point %r of state %r sits in region %r, '
                                 'not in the first region' %
                                 (point.id, node.id, region.id),
                                 elem=point.elem)
