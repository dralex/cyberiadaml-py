# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The layered layout of the hierarchical trees
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
"""The layered layout of the trees (docs/reconstruction.md of libhtreegeom).

A port of htgeom_layout.cpp: the phases P1-P10 in the same order and with
the same arithmetic, so the layout comes out the same.
"""
import math
from typing import Dict, List, Optional, Set, Tuple

from .transform import (attach_edge_minimal, clean_tree_geometry,
                        node_is_comment, project_edge_to_borders,
                        reconstruct_edge_loop, shift_subtree,
                        tree_bounding_rect)
from .types import (BAD_PARAMETER, COMMENT, COMPOSITE, COORD_EPS, FLOW_DOWN,
                    FLOW_RIGHT, LABEL_HEIGHT, LABEL_WIDTH, LAYER_GAP,
                    LAYOUT_ADAPTIVE, LAYOUT_ALTERNATE, LAYOUT_ASPECT,
                    LAYOUT_FIXED, LAYOUT_SWEEPS, NODE_GAP, NODE_HEIGHT,
                    NODE_WIDTH, PADDING, POINT, POINT_SIZE, REGION,
                    ROLE_DEEP_HISTORY, ROLE_ENTRY_POINT, ROLE_EXIT_POINT,
                    ROLE_FINAL, ROLE_INITIAL, ROLE_NONE, ROLE_SHALLOW_HISTORY,
                    ROLE_TERMINATE, TREE, Edge, GeometryError, LayoutOptions,
                    Node, Point, Rect, Tree)

# the vertex kinds
VERTEX_REAL = 0             # a child of the container
VERTEX_EDGE_DUMMY = 1       # a bend of a long edge
VERTEX_LABEL_DUMMY = 2      # the label slot of a transition
VERTEX_VIRTUAL = 3          # ENTRY / EXIT

# the container kinds
CONTAINER_LEAF = 0          # no layout content
CONTAINER_GRAPH = 1         # states and pseudostates: a layered graph
CONTAINER_REGIONS = 2       # the regions of a composite

HUGE = 1e300


def check_options(opts: LayoutOptions) -> LayoutOptions:
    if opts.direction not in (FLOW_DOWN, FLOW_RIGHT) or \
            opts.mode not in (LAYOUT_FIXED, LAYOUT_ALTERNATE,
                              LAYOUT_ADAPTIVE):
        raise GeometryError(BAD_PARAMETER, 'bad layout options')
    out = opts.copy()
    for name, default in (('aspect', LAYOUT_ASPECT), ('node_gap', NODE_GAP),
                          ('layer_gap', LAYER_GAP), ('padding', PADDING),
                          ('sweeps', LAYOUT_SWEEPS),
                          ('node_width', NODE_WIDTH),
                          ('node_height', NODE_HEIGHT),
                          ('point_size', POINT_SIZE),
                          ('label_width', LABEL_WIDTH),
                          ('label_height', LABEL_HEIGHT)):
        if getattr(out, name) <= 0:
            setattr(out, name, default)
    return out


class Vertex:
    """A vertex of the layout graph of a container."""

    def __init__(self, kind: int = VERTEX_VIRTUAL) -> None:
        self.node: Optional[Node] = None
        self.role = ROLE_NONE
        self.kind = kind
        self.edge = -1              # the layout edge of a dummy
        self.layer = 0
        self.order = 0              # the index inside the layer
        self.flow_size = 0.0
        self.cross_size = 0.0
        self.before = 0.0           # the cross-axis extents around the anchor
        self.after = 0.0
        self.flow = 0.0             # the anchor in the frame
        self.cross = 0.0
        self.seed = False           # the update: the vertex had geometry
        self.seed_x = 0.0           # its centre in the document
        self.seed_y = 0.0
        self.seed_flow = 0.0        # its centre in the frame
        self.seed_cross = 0.0
        self.seed_layer = 0         # its band among the seeded vertices, 1..


class LayoutEdge:
    """An edge of the layout graph, in the layout direction."""

    def __init__(self, source: int, target: int, edge: Edge) -> None:
        self.source = source
        self.target = target
        self.edge = edge
        self.reversed = False
        self.has_label = False
        self.label_w = 0.0
        self.label_h = 0.0
        self.drawn_ends = False     # the update: between two drawn vertices
        self.chain: List[int] = []  # source, dummies, target by layer


class Graph:
    """The layout graph of one container."""

    def __init__(self) -> None:
        self.direction = FLOW_RIGHT
        self.update = False
        self.vertices: List[Vertex] = []   # ENTRY, the children, EXIT, dummies
        self.edges: List[LayoutEdge] = []
        self.layers: List[List[int]] = []  # 0 = ENTRY .. last + 1 = EXIT
        self.up: List[List[int]] = []
        self.down: List[List[int]] = []
        self.entry = 0
        self.exit = 0
        self.last = 0
        self.band_lo: List[float] = []     # the update: a drawn layer extent
        self.band_hi: List[float] = []
        self.band_drawn: List[int] = []


class Seed:
    """A lifted edge of a container."""

    def __init__(self, edge: Edge, source_child: int, target_child: int,
                 self_loop: bool, has_label: bool) -> None:
        self.edge = edge
        self.source_child = source_child    # -1 = ENTRY
        self.target_child = target_child    # -1 = EXIT
        self.self_loop = self_loop
        self.has_label = has_label


class Piece:
    """The route of an edge inside a container."""

    def __init__(self, edge: Edge) -> None:
        self.edge = edge
        self.bends: List[Point] = []        # container coordinates
        self.has_label = False
        self.label = Rect()


class Container:
    """A container of the tree: the root, a composite, a region."""

    def __init__(self, node: Optional[Node], level: int,
                 direction: int) -> None:
        self.node = node                # None: the pseudo root of a list
        self.kind = CONTAINER_LEAF
        self.level = level
        self.direction = direction      # of the content
        self.children: List[Node] = []  # the vertex children in order
        self.seeds: List[Seed] = []
        self.pieces: List[Piece] = []
        self.shelf = 0.0                # the comment shelf cursor


class Context:
    """One layout pass of a tree."""

    def __init__(self, tree: Tree, opts: LayoutOptions, start: int,
                 reconstruct_sm: bool, update: bool) -> None:
        self.tree = tree
        self.opts = opts
        self.start = start              # the root frame of this pass
        self.reconstruct_sm = reconstruct_sm
        self.sm_had_rect = False
        self.update = update            # the existing geometry is the seed
        self.containers: List[Container] = []   # pre-order, 0 = the root
        self.index: Dict[Node, int] = {}
        self.seeds: Dict[Node, Point] = {}      # the centres before
        self.edge_seeds: Set[Edge] = set()      # the edges with geometry
        self.routed: Set[Edge] = set()          # routed in this pass


def _seeded(ctx: Context, node: Node) -> Optional[Point]:
    return ctx.seeds.get(node)


def _source_role(r: int) -> bool:
    return r in (ROLE_INITIAL, ROLE_ENTRY_POINT, ROLE_SHALLOW_HISTORY,
                 ROLE_DEEP_HISTORY)


def _sink_role(r: int) -> bool:
    return r in (ROLE_FINAL, ROLE_TERMINATE, ROLE_EXIT_POINT)


def _is_border_point(n: Optional[Node]) -> bool:
    # An entry/exit point on the border of a nested container.
    return n is not None and n.type == POINT and \
        n.role in (ROLE_ENTRY_POINT, ROLE_EXIT_POINT) and \
        n.parent is not None and n.parent.type != TREE


def _is_vertex(n: Optional[Node]) -> bool:
    return n is not None and n.type != COMMENT and n.type != REGION and \
        not _is_border_point(n)


def _is_container(n: Optional[Node]) -> bool:
    return n is not None and n.type != POINT and n.type != COMMENT and \
        (bool(n.children) or n.type in (COMPOSITE, REGION, TREE))


def _is_composite(n: Optional[Node]) -> bool:
    # A container drawn with its own border.
    return n is not None and n.type != REGION and n.type != TREE


def _to_doc(d: int, flow: float, cross: float) -> Tuple[float, float]:
    return (cross, flow) if d == FLOW_DOWN else (flow, cross)


def _size_to_frame(d: int, w: float, h: float) -> Tuple[float, float]:
    return (h, w) if d == FLOW_DOWN else (w, h)


def _preferred(o: LayoutOptions, start: int, level: int) -> int:
    # The preferred frame of a nesting level: alternating by depth.
    if o.mode != LAYOUT_FIXED and level % 2 == 1:
        return FLOW_RIGHT if start == FLOW_DOWN else FLOW_DOWN
    return start


def _target(o: LayoutOptions, preferred: int) -> float:
    return o.aspect if preferred == FLOW_RIGHT else 1.0 / o.aspect


def _shape_distance(w: float, h: float, target: float) -> float:
    if w <= 0.0 or h <= 0.0:
        return 0.0
    return abs(math.log((w / h) / target))


def _on_side(w: float, h: float, target: float) -> bool:
    wide = w <= 0.0 or h <= 0.0 or w >= h
    return wide == (target >= 1.0)


def _shape_better(w1: float, h1: float, w2: float, h2: float,
                  target: float) -> int:
    """Return 0 for the first shape, 1 for the second, -1 for a tie."""
    s1, s2 = _on_side(w1, h1, target), _on_side(w2, h2, target)
    if s1 != s2:
        return 0 if s1 else 1
    d1 = _shape_distance(w1, h1, target)
    d2 = _shape_distance(w2, h2, target)
    if abs(d1 - d2) < COORD_EPS:
        return -1
    return 0 if d1 < d2 else 1


def _choose(w_down: float, h_down: float, w_right: float, h_right: float,
            target: float, preferred: int) -> int:
    better = _shape_better(w_down, h_down, w_right, h_right, target)
    if better < 0:
        return preferred
    return FLOW_DOWN if better == 0 else FLOW_RIGHT


def _first_children(ctx: Context, ci: int) -> List[Node]:
    c = ctx.containers[ci]
    return c.node.children if c.node is not None else ctx.tree.nodes


def _container_of(ctx: Context, node: Optional[Node]) -> int:
    # The container whose child list holds the node, -1 for the root.
    if node is None:
        return -1
    if node.parent is None:
        return -1 if ctx.containers[0].node is node else 0
    return ctx.index.get(node.parent, -1)


def _child_containing(ctx: Context, ci: int, x: Optional[Node]) -> int:
    c = ctx.containers[ci]
    while x is not None and x.parent is not c.node:
        x = x.parent
    if x is None:
        return -1
    for k, child in enumerate(c.children):
        if child is x:
            return k
    return -1


def _collect(ctx: Context, node: Optional[Node], level: int) -> None:
    ci = len(ctx.containers)
    c = Container(node, level, _preferred(ctx.opts, ctx.start, level))
    ctx.containers.append(c)
    if node is not None:
        ctx.index[node] = ci
    first = _first_children(ctx, ci)
    has_region = has_vertex = False
    for child in first:
        if child.type == REGION:
            has_region = True
        if _is_vertex(child):
            has_vertex = True
            c.children.append(child)
    c.kind = CONTAINER_REGIONS if has_region else \
        (CONTAINER_GRAPH if has_vertex else CONTAINER_LEAF)
    for child in first:
        if _is_container(child):
            _collect(ctx, child, level + (0 if child.type == REGION else 1))


def _seed_edges(ctx: Context) -> None:
    """Seed every graph container on the nesting path of a transition."""
    for e in ctx.tree.edges:
        if e.source is None or e.target is None or \
                node_is_comment(e.source) or node_is_comment(e.target):
            continue
        chain_s: List[int] = []
        chain_t: List[int] = []
        c_ = _container_of(ctx, e.source)
        while c_ >= 0:
            chain_s.append(c_)
            c_ = _container_of(ctx, ctx.containers[c_].node)
        c_ = _container_of(ctx, e.target)
        while c_ >= 0:
            chain_t.append(c_)
            c_ = _container_of(ctx, ctx.containers[c_].node)
        lca = -1
        for item in chain_t:
            if item in chain_s:
                lca = item
                break
        if lca < 0:
            continue
        for item in chain_s:
            if item == lca:
                break
            c = ctx.containers[item]
            if c.kind != CONTAINER_GRAPH:
                continue
            s = Seed(e, _child_containing(ctx, item, e.source), -1, False,
                     e.label_rect is not None and
                     c.node is e.source.parent)
            if s.source_child >= 0:
                c.seeds.append(s)
        for item in chain_t:
            if item == lca:
                break
            c = ctx.containers[item]
            if c.kind != CONTAINER_GRAPH:
                continue
            s = Seed(e, -1, _child_containing(ctx, item, e.target), False,
                     False)
            if s.target_child >= 0:
                c.seeds.append(s)
        c = ctx.containers[lca]
        if c.kind == CONTAINER_GRAPH:
            sc = _child_containing(ctx, lca, e.source)
            tc = _child_containing(ctx, lca, e.target)
            if sc < 0 and tc < 0:
                continue
            loop = sc == tc
            c.seeds.append(Seed(e, sc, tc, loop,
                                e.label_rect is not None and not loop and
                                c.node is e.source.parent and sc >= 0))


def _count_runs(ctx: Context, ci: int) -> Tuple[int, int]:
    # The transitions between two drawn children: right and down runs.
    c = ctx.containers[ci]
    right = down = 0
    for sd in c.seeds:
        if sd.self_loop or sd.source_child < 0 or sd.target_child < 0:
            continue
        a = _seeded(ctx, c.children[sd.source_child])
        b = _seeded(ctx, c.children[sd.target_child])
        if a is None or b is None:
            continue
        dx = b.x - a.x
        dy = b.y - a.y
        if dx > abs(dy):
            right += 1
        elif dy > abs(dx):
            down += 1
    return right, down


def _regions(ctx: Context, c: Container) -> List[int]:
    assert c.node is not None
    return [ctx.index[r] for r in c.node.children
            if r.type == REGION and r in ctx.index]


def _infer_directions(ctx: Context) -> None:
    # The update: the flow of a drawn container from its transitions.
    for ci, c in enumerate(ctx.containers):
        if c.node is not None and c.node.type == REGION:
            continue        # set by the composite
        right = down = 0
        if c.kind == CONTAINER_REGIONS:
            for ri in _regions(ctx, c):
                r, d = _count_runs(ctx, ri)
                right += r
                down += d
        else:
            right, down = _count_runs(ctx, ci)
        if right > down:
            c.direction = FLOW_RIGHT
        elif down > right:
            c.direction = FLOW_DOWN
        else:
            c.direction = _preferred(ctx.opts, ctx.start, c.level)
        if ci == 0:
            ctx.start = c.direction
        if c.kind == CONTAINER_REGIONS:
            for ri in _regions(ctx, c):
                ctx.containers[ri].direction = c.direction


# the layered layout of one graph container: P2 - P6


def _build_graph(ctx: Context, ci: int) -> Graph:
    c = ctx.containers[ci]
    o = ctx.opts
    n = len(c.children)
    g = Graph()
    g.direction = c.direction
    g.update = ctx.update
    g.vertices = [Vertex() for _ in range(n + 2)]
    g.entry = 0
    g.exit = n + 1
    g.last = 0
    for k in range(1, n + 1):
        v = g.vertices[k]
        node = c.children[k - 1]
        v.node = node
        v.role = node.role
        v.kind = VERTEX_REAL
        if ctx.update:
            centre = _seeded(ctx, node)
            if centre is not None:
                v.seed = True
                v.seed_x = centre.x
                v.seed_y = centre.y
        if node.rect is not None:
            v.flow_size, v.cross_size = _size_to_frame(
                c.direction, node.rect.width, node.rect.height)
        else:
            v.flow_size = v.cross_size = o.point_size
        v.before = v.after = v.cross_size / 2.0
    for s in c.seeds:
        if s.self_loop:
            continue
        drawn_ends = ctx.update and \
            (s.source_child < 0 or g.vertices[s.source_child + 1].seed) and \
            (s.target_child < 0 or g.vertices[s.target_child + 1].seed)
        if drawn_ends and (s.source_child < 0 or s.target_child < 0 or
                           s.edge in ctx.edge_seeds):
            # a drawn transition between drawn elements keeps its geometry
            continue
        e = LayoutEdge(g.entry if s.source_child < 0 else s.source_child + 1,
                       g.exit if s.target_child < 0 else s.target_child + 1,
                       s.edge)
        e.drawn_ends = drawn_ends
        # a new edge between drawn vertices takes no label layer
        e.has_label = s.has_label and not drawn_ends
        if s.has_label:
            lr = s.edge.label_rect
            assert lr is not None
            e.label_w = lr.width if lr.width > 0.0 else o.label_width
            e.label_h = lr.height if lr.height > 0.0 else o.label_height
        g.edges.append(e)
    return g


def _reverse_edge(e: LayoutEdge) -> None:
    e.source, e.target = e.target, e.source
    e.reversed = not e.reversed


def _break_cycles(g: Graph) -> List[int]:
    """P2: reverse the back edges; return the topological order."""
    n = len(g.vertices)
    for e in g.edges:
        sv = g.vertices[e.source]
        tv = g.vertices[e.target]
        if g.update and sv.seed and tv.seed:
            # the drawing decides: a transition running backward
            if tv.seed_flow < sv.seed_flow - COORD_EPS:
                _reverse_edge(e)
            continue
        if g.update and (sv.seed or tv.seed):
            continue    # the roles of the drawn vertices stay drawn
        if (_source_role(tv.role) and e.source != g.entry) or \
                (_sink_role(sv.role) and e.target != g.exit):
            _reverse_edge(e)
    bands = 0
    node_of = list(range(n))
    for v in range(n):
        vx = g.vertices[v]
        if g.update and vx.seed and vx.seed_layer > 0:
            node_of[v] = n + vx.seed_layer - 1
            if vx.seed_layer > bands:
                bands = vx.seed_layer
    total = n + bands
    out: List[List[int]] = [[] for _ in range(total)]
    members: List[List[int]] = [[] for _ in range(total)]
    colour = [0] * total
    indeg = [0] * total
    for b in range(bands - 1):
        out[n + b].append(-1)       # the chain to the next band
    for v in range(n):
        if node_of[v] != v:
            members[node_of[v]].append(v)
    for k, e in enumerate(g.edges):
        out[node_of[e.source]].append(k)
        indeg[node_of[e.target]] += 1
    roots: List[int] = []
    if bands > 0:
        roots.append(n)
    roots += [node_of[v] for v in range(n)
              if _source_role(g.vertices[v].role)]
    roots += [node_of[v] for v in range(n) if indeg[node_of[v]] == 0]
    roots += list(range(total))
    topo: List[int] = []
    for root in roots:
        if colour[root]:
            continue
        stack = [[root, 0]]
        colour[root] = 1
        while stack:
            top = stack[-1]
            v = top[0]
            if top[1] < len(out[v]):
                k = out[v][top[1]]
                top[1] += 1
                if k < 0:
                    w = v + 1
                    if colour[w] == 0:
                        colour[w] = 1
                        stack.append([w, 0])
                    continue
                e = g.edges[k]
                w = node_of[e.target]
                if colour[w] == 0:
                    colour[w] = 1
                    stack.append([w, 0])
                elif colour[w] == 1:
                    _reverse_edge(e)
            else:
                colour[v] = 2
                if v >= n:
                    topo.extend(reversed(members[v]))
                else:
                    topo.append(v)
                stack.pop()
    topo.reverse()
    return topo


def _seed_bands(g: Graph) -> None:
    # The update: the drawn vertices along the flow fall into bands.
    order = []
    for v in range(1, len(g.vertices) - 1):
        vx = g.vertices[v]
        if vx.kind == VERTEX_REAL and vx.seed:
            order.append((vx.seed_flow - vx.flow_size / 2.0, v))
    order.sort()
    band_end = 0.0
    band = 0
    for start, v in order:
        vx = g.vertices[v]
        end = vx.seed_flow + vx.flow_size / 2.0
        if band == 0 or start > band_end - COORD_EPS:
            band += 1
            band_end = end
        elif end > band_end:
            band_end = end
        vx.seed_layer = band


def _assign_layers(g: Graph, topo: List[int]) -> None:
    """P3: the longest-path layering with the pinned roles."""
    n = len(g.vertices)
    incoming: List[List[int]] = [[] for _ in range(n)]
    for k, e in enumerate(g.edges):
        incoming[e.target].append(k)
    has_source = any(g.vertices[v].kind == VERTEX_REAL and
                     _source_role(g.vertices[v].role) and
                     not (g.update and g.vertices[v].seed)
                     for v in range(1, n))
    bands = 0
    if g.update:
        for v in range(1, n - 1):
            if g.vertices[v].seed_layer > bands:
                bands = g.vertices[v].seed_layer
    band_layer = list(range(bands + 1))
    for _ in range(bands + 1):
        changed = False
        for v in topo:
            vx = g.vertices[v]
            if v == g.entry:
                layer = 0
            elif v == g.exit:
                layer = 1
            elif vx.seed:
                layer = band_layer[vx.seed_layer]
            else:
                layer = 2 if has_source and not _source_role(vx.role) else 1
            for k in incoming[v]:
                e = g.edges[k]
                need = g.vertices[e.source].layer + (2 if e.has_label else 1)
                if need > layer:
                    layer = need
            vx.layer = layer
        if not g.update:
            break
        # a pushed band drags the later bands along, as whole bands
        floor = 0
        for b in range(1, bands + 1):
            top = 0
            for v in range(1, n - 1):
                vx = g.vertices[v]
                if vx.seed_layer == b and vx.layer > top:
                    top = vx.layer
            if top < floor + 1:
                top = floor + 1
            if band_layer[b] != top:
                changed = True
            band_layer[b] = top
            for v in range(1, n - 1):
                vx = g.vertices[v]
                if vx.seed_layer == b:
                    vx.layer = top
            floor = top
        if not changed:
            break
    # the sinks close the flow in a common last layer
    sink_layer = 0
    max_layer = 0
    for v in range(1, n - 1):
        vx = g.vertices[v]
        if _sink_role(vx.role) and not (g.update and vx.seed):
            if vx.layer > sink_layer:
                sink_layer = vx.layer
        elif vx.layer > max_layer:
            max_layer = vx.layer
    if 0 < sink_layer < max_layer + 1:
        sink_layer = max_layer + 1
    for v in range(1, n - 1):
        vx = g.vertices[v]
        if _sink_role(vx.role) and not (g.update and vx.seed):
            vx.layer = sink_layer
    g.last = sink_layer if sink_layer > max_layer else max_layer
    exit_layer = g.last + 1
    for k in incoming[g.exit]:
        e = g.edges[k]
        need = g.vertices[e.source].layer + (2 if e.has_label else 1)
        if need > exit_layer:
            exit_layer = need
    g.vertices[g.exit].layer = exit_layer
    g.last = exit_layer - 1


def _add_dummy(g: Graph, kind: int, edge: int, layer: int, flow_size: float,
               before: float, after: float) -> int:
    v = Vertex(kind)
    v.edge = edge
    v.layer = layer
    v.flow_size = flow_size
    v.cross_size = before + after
    v.before = before
    v.after = after
    g.vertices.append(v)
    return len(g.vertices) - 1


def _insert_dummies(g: Graph, o: LayoutOptions) -> None:
    """P4: the proper layering with the edge and label dummies."""
    for k, e in enumerate(g.edges):
        ls = g.vertices[e.source].layer
        lt = g.vertices[e.target].layer
        label_layer = -1
        e.chain = [e.source]
        if e.has_label:
            label_layer = lt - 1 if e.reversed else ls + 1
        for layer in range(ls + 1, lt):
            if layer == label_layer:
                # the slot: the line at the anchor, the label after it
                if g.direction == FLOW_DOWN:
                    fs, cs = e.label_h, e.label_w
                else:
                    fs, cs = e.label_w, e.label_h
                e.chain.append(_add_dummy(g, VERTEX_LABEL_DUMMY, k, layer, fs,
                                          o.padding / 2.0,
                                          cs + o.padding / 2.0))
            else:
                e.chain.append(_add_dummy(g, VERTEX_EDGE_DUMMY, k, layer,
                                          0.0, 0.0, 0.0))
        e.chain.append(e.target)
    g.layers = [[] for _ in range(g.last + 2)]
    for v, vx in enumerate(g.vertices):
        layer_list = g.layers[vx.layer]
        vx.order = len(layer_list)
        layer_list.append(v)
    if g.update:
        # the drawn vertices by their drawn cross position, the others after
        for layer in range(g.last + 2):
            keyed = sorted((g.vertices[v].seed_cross if g.vertices[v].seed
                            else HUGE, v) for v in g.layers[layer])
            g.layers[layer] = [v for _, v in keyed]
            _reindex(g, layer)
    g.up = [[] for _ in g.vertices]
    g.down = [[] for _ in g.vertices]
    for e in g.edges:
        ch = e.chain
        for i in range(len(ch) - 1):
            g.down[ch[i]].append(ch[i + 1])
            g.up[ch[i + 1]].append(ch[i])


# P5: the barycentre ordering


def _reindex(g: Graph, layer: int) -> None:
    for i, v in enumerate(g.layers[layer]):
        g.vertices[v].order = i


def _position(g: Graph, v: int, ref_size: int) -> float:
    # A virtual vertex reports the centre of the layer being sorted.
    if g.vertices[v].kind == VERTEX_VIRTUAL:
        return (ref_size - 1) / 2.0
    return float(g.vertices[v].order)


def _barycentres(g: Graph, layer: int, fixed_up: bool) -> List[float]:
    result = []
    nodes = g.layers[layer]
    for v in nodes:
        nb = g.up[v] if fixed_up else g.down[v]
        if not nb or (g.update and g.vertices[v].seed):
            result.append(float(g.vertices[v].order))
        else:
            total = 0.0
            for w in nb:
                total += _position(g, w, len(nodes))
            result.append(total / len(nb))
    return result


def _sort_layer(g: Graph, layer: int, fixed_up: bool) -> bool:
    nodes = g.layers[layer]
    if len(nodes) < 2:
        return False
    b = _barycentres(g, layer, fixed_up)
    keyed = sorted(zip(b, nodes), key=lambda p: p[0])
    changed = any(nodes[i] != keyed[i][1] for i in range(len(nodes)))
    g.layers[layer] = [v for _, v in keyed]
    _reindex(g, layer)
    return changed


def _graph_copy(g: Graph) -> Graph:
    result = Graph()
    result.direction = g.direction
    result.update = g.update
    result.vertices = []
    for vx in g.vertices:
        copy = Vertex(vx.kind)
        copy.__dict__.update(vx.__dict__)
        result.vertices.append(copy)
    result.edges = []
    for e in g.edges:
        copy_e = LayoutEdge(e.source, e.target, e.edge)
        copy_e.__dict__.update(e.__dict__)
        copy_e.chain = list(e.chain)
        result.edges.append(copy_e)
    result.layers = [list(layer) for layer in g.layers]
    result.up = [list(x) for x in g.up]
    result.down = [list(x) for x in g.down]
    result.entry, result.exit, result.last = g.entry, g.exit, g.last
    result.band_lo = list(g.band_lo)
    result.band_hi = list(g.band_hi)
    result.band_drawn = list(g.band_drawn)
    return result


def _count_crossings(g: Graph) -> int:
    total = 0
    for layer in range(g.last + 1):
        p = []
        for v in g.layers[layer]:
            for w in g.down[v]:
                p.append((g.vertices[v].order, g.vertices[w].order))
        for a in range(len(p)):
            for c in range(a + 1, len(p)):
                if (p[a][0] < p[c][0] and p[a][1] > p[c][1]) or \
                        (p[a][0] > p[c][0] and p[a][1] < p[c][1]):
                    total += 1
    return total


class _Best:
    def __init__(self, g: Graph) -> None:
        self.layers = [list(layer) for layer in g.layers]
        self.crossings = _count_crossings(g)

    def keep(self, g: Graph) -> None:
        k = _count_crossings(g)
        if k < self.crossings:
            self.crossings = k
            self.layers = [list(layer) for layer in g.layers]


def _order_phase1(g: Graph, sweeps: int, best: _Best) -> None:
    """Sweep DOWN and UP, keeping the best order aside."""
    s = 0
    while s < sweeps and best.crossings > 0:
        changed = False
        for layer in range(1, g.last + 2):
            changed |= _sort_layer(g, layer, True)
        for layer in range(g.last, -1, -1):
            changed |= _sort_layer(g, layer, False)
        best.keep(g)
        if not changed:
            break
        s += 1


def _order_phase2(g: Graph) -> bool:
    """Reverse the blocks of equal barycentres."""
    any_ = False
    for layer in range(1, g.last + 1):
        nodes = g.layers[layer]
        if len(nodes) < 2:
            continue
        b = _barycentres(g, layer, True)
        i = 0
        while i < len(nodes):
            j = i + 1
            drawn = g.update and g.vertices[nodes[i]].seed
            while j < len(nodes) and abs(b[j] - b[i]) < COORD_EPS:
                if g.update and g.vertices[nodes[j]].seed:
                    drawn = True
                j += 1
            if j - i > 1 and not drawn:
                nodes[i:j] = nodes[i:j][::-1]
                any_ = True
            i = j
        _reindex(g, layer)
    return any_


def _order(g: Graph, o: LayoutOptions) -> None:
    best = _Best(g)
    _order_phase1(g, o.sweeps, best)
    r = 0
    while r < o.sweeps and best.crossings > 0:
        if not _order_phase2(g):
            break
        best.keep(g)
        _order_phase1(g, o.sweeps, best)
        r += 1
    g.layers = best.layers
    for layer in range(g.last + 2):
        _reindex(g, layer)


# P6: the priority layout on the cross axis, the bands on the flow axis


def _gap(g: Graph, o: LayoutOptions, u: int, v: int) -> float:
    if g.vertices[u].kind == VERTEX_EDGE_DUMMY and \
            g.vertices[v].kind == VERTEX_EDGE_DUMMY:
        return o.padding
    if g.update and g.vertices[u].seed and g.vertices[v].seed:
        return 0.0      # the drawn neighbours keep their drawn gap
    return o.node_gap


def _pack_layer(g: Graph, o: LayoutOptions, layer: int) -> None:
    nodes = g.layers[layer]
    pos = 0.0
    for i, w in enumerate(nodes):
        v = g.vertices[w]
        if i > 0:
            pos += _gap(g, o, nodes[i - 1], w) + v.before
        else:
            pos = v.before
        if g.update and v.seed and v.seed_cross > pos:
            pos = v.seed_cross
        v.cross = pos
        pos += v.after


def _centre_virtual(g: Graph) -> None:
    # The virtual vertices sit at the centre of the content.
    lo = hi = 0.0
    any_ = False
    for vx in g.vertices:
        if vx.kind == VERTEX_VIRTUAL:
            continue
        a = vx.cross - vx.before
        b = vx.cross + vx.after
        if not any_ or a < lo:
            lo = a
        if not any_ or b > hi:
            hi = b
        any_ = True
    g.vertices[g.entry].cross = (lo + hi) / 2.0
    g.vertices[g.exit].cross = (lo + hi) / 2.0


def _block_mean(bsum: List[float], bw: List[float], bdsum: List[float],
                bdn: List[int], k: int) -> float:
    return bdsum[k] / float(bdn[k]) if bdn[k] > 0 else bsum[k] / bw[k]


def _priority_pass(g: Graph, o: LayoutOptions, layer: int,
                   fixed_up: bool) -> None:
    # The weighted least-squares placement of a layer, the order kept.
    nodes = g.layers[layer]
    n = len(nodes)
    if n == 0:
        return
    off = [0.0] * n
    d = [0.0] * n
    w = [0.0] * n
    top = float(len(g.vertices)) + 1.0
    _centre_virtual(g)
    for i in range(n):
        v = g.vertices[nodes[i]]
        nb = g.up[nodes[i]] if fixed_up else g.down[nodes[i]]
        if i > 0:
            off[i] = off[i - 1] + g.vertices[nodes[i - 1]].after + \
                _gap(g, o, nodes[i - 1], nodes[i]) + v.before
        if g.update and v.seed:
            # a drawn vertex aims at its drawn place above every pull
            d[i] = v.seed_cross
            w[i] = top * top
        elif not nb:
            d[i] = v.cross
            w[i] = COORD_EPS
        else:
            total = 0.0
            for k in nb:
                total += g.vertices[k].cross
            d[i] = total / len(nb)
            w[i] = float(len(nb)) if v.kind == VERTEX_REAL else top
        d[i] -= off[i]
    bsum: List[float] = []
    bw: List[float] = []
    bdsum: List[float] = []
    bdn: List[int] = []
    bstart: List[int] = []
    for i in range(n):
        drawn = g.update and g.vertices[nodes[i]].seed
        bsum.append(w[i] * d[i])
        bw.append(w[i])
        bdsum.append(d[i] if drawn else 0.0)
        bdn.append(1 if drawn else 0)
        bstart.append(i)
        while len(bsum) > 1 and \
                _block_mean(bsum, bw, bdsum, bdn, len(bsum) - 1) < \
                _block_mean(bsum, bw, bdsum, bdn, len(bsum) - 2):
            bsum[-2] += bsum[-1]
            bw[-2] += bw[-1]
            bdsum[-2] += bdsum[-1]
            bdn[-2] += bdn[-1]
            bsum.pop()
            bw.pop()
            bdsum.pop()
            bdn.pop()
            bstart.pop()
    for k in range(len(bstart)):
        end = bstart[k + 1] if k + 1 < len(bstart) else n
        m = _block_mean(bsum, bw, bdsum, bdn, k)
        for i in range(bstart[k], end):
            g.vertices[nodes[i]].cross = m + off[i]


def _assign_coordinates(g: Graph, o: LayoutOptions) -> None:
    t = (g.last + 1) // 2
    start = 0.0
    for layer in range(1, g.last + 1):
        _pack_layer(g, o, layer)
    for layer in range(1, g.last + 1):
        _priority_pass(g, o, layer, True)
    for layer in range(g.last - 1, 0, -1):
        _priority_pass(g, o, layer, False)
    for layer in range(1 if t < 1 else t, g.last + 1):
        _priority_pass(g, o, layer, True)
    if g.update:
        # the drawn bands keep their drawn flow positions
        cursor = shift = 0.0
        any_ = after_new = False
        g.band_lo = [0.0] * (g.last + 2)
        g.band_hi = [0.0] * (g.last + 2)
        g.band_drawn = [0] * (g.last + 2)
        for layer in range(1, g.last + 1):
            nodes = g.layers[layer]
            lo = hi = tall = 0.0
            seeded = False
            for w in nodes:
                vx = g.vertices[w]
                if vx.seed:
                    a = vx.seed_flow - vx.flow_size / 2.0
                    b = vx.seed_flow + vx.flow_size / 2.0
                    if not seeded or a < lo:
                        lo = a
                    if not seeded or b > hi:
                        hi = b
                    seeded = True
                elif vx.flow_size > tall:
                    tall = vx.flow_size
            if seeded:
                need = cursor + (o.layer_gap if after_new else 0.0) \
                    if any_ else lo + shift
                if lo + shift < need:
                    shift = need - lo
                lo += shift
                hi += shift
                if hi - lo < tall:
                    hi = lo + tall
                for w in nodes:
                    vx = g.vertices[w]
                    vx.flow = vx.seed_flow + shift if vx.seed \
                        else (lo + hi) / 2.0
                g.band_lo[layer] = lo
                g.band_hi[layer] = hi
                g.band_drawn[layer] = 1
                cursor = hi
                after_new = False
            else:
                from_ = cursor + o.layer_gap if any_ else 0.0
                for w in nodes:
                    g.vertices[w].flow = from_ + tall / 2.0
                cursor = from_ + tall
                after_new = True
            any_ = True
        g.vertices[g.entry].flow = 0.0
        g.vertices[g.exit].flow = cursor
        return
    for layer in range(1, g.last + 1):
        nodes = g.layers[layer]
        band = 0.0
        for w in nodes:
            if g.vertices[w].flow_size > band:
                band = g.vertices[w].flow_size
        for w in nodes:
            g.vertices[w].flow = start + band / 2.0
        start += band + o.layer_gap
    g.vertices[g.entry].flow = 0.0
    g.vertices[g.exit].flow = start - o.layer_gap \
        if start > o.layer_gap else 0.0


def _segment_in_box(p: Point, q: Point, f0: float, f1: float, c0: float,
                    c1: float) -> bool:
    # The segment (x = flow, y = cross) meets the box.
    t0, t1 = 0.0, 1.0
    dp = (p.x - q.x, q.x - p.x, p.y - q.y, q.y - p.y)
    dq = (p.x - f0, f1 - p.x, p.y - c0, c1 - p.y)
    for k in range(4):
        if abs(dp[k]) < COORD_EPS:
            if dq[k] < 0.0:
                return False
            continue
        r = dq[k] / dp[k]
        if dp[k] < 0.0:
            if r > t1:
                return False
            if r > t0:
                t0 = r
        else:
            if r < t0:
                return False
            if r < t1:
                t1 = r
    return True


def _segment_cross(p: Point, q: Point, f0: float,
                   f1: float) -> Tuple[float, float]:
    # The cross extent of the segment over the flow span.
    ta, tb = 0.0, 1.0
    if abs(q.x - p.x) > COORD_EPS:
        ta = (f0 - p.x) / (q.x - p.x)
        tb = (f1 - p.x) / (q.x - p.x)
        if ta > tb:
            ta, tb = tb, ta
        if ta < 0.0:
            ta = 0.0
        if tb > 1.0:
            tb = 1.0
    a = p.y + (q.y - p.y) * ta
    b = p.y + (q.y - p.y) * tb
    return (a, b) if a < b else (b, a)


def _drawn_route(ctx: Context, ci: int, g: Graph,
                 e: Edge) -> Optional[List[Point]]:
    # The update: the frame route of a drawn transition that stays.
    if e.source is None or e.target is None or e not in ctx.edge_seeds:
        return None
    sc = _child_containing(ctx, ci, e.source)
    tc = _child_containing(ctx, ci, e.target)
    if sc < 0 or tc < 0 or sc == tc:
        return None
    sv = g.vertices[sc + 1]
    tv = g.vertices[tc + 1]
    if not sv.seed or not tv.seed:
        return None
    df = sv.flow - sv.seed_flow
    dc = sv.cross - sv.seed_cross
    if abs(tv.flow - tv.seed_flow - df) > COORD_EPS or \
            abs(tv.cross - tv.seed_cross - dc) > COORD_EPS:
        return None
    s0 = _seeded(ctx, e.source)
    t0 = _seeded(ctx, e.target)
    if s0 is None or t0 is None:
        return None
    route = [(e.source_point if e.source_point is not None else s0).copy()]
    route += [p.copy() for p in e.polyline or []]
    route.append((e.target_point if e.target_point is not None
                  else t0).copy())
    for p in route:
        x, y = p.x, p.y
        p.x = (y if g.direction == FLOW_DOWN else x) + df
        p.y = (x if g.direction == FLOW_DOWN else y) + dc
    return route


def _clear_routes(ctx: Context, ci: int, g: Graph) -> None:
    # The update: move a new vertex or bend off a drawn route that stays.
    o = ctx.opts
    routes = []
    for e in ctx.tree.edges:
        route = _drawn_route(ctx, ci, g, e)
        if route is not None:
            routes.append(route)
    if not routes:
        return
    for layer in range(1, g.last + 1):
        nodes = g.layers[layer]
        for i in range(len(nodes)):
            v = g.vertices[nodes[i]]
            band = v.kind != VERTEX_REAL and layer < len(g.band_drawn) and \
                bool(g.band_drawn[layer])
            if v.kind == VERTEX_VIRTUAL or v.seed:
                continue
            before = after = False
            for j in range(len(nodes)):
                if not g.vertices[nodes[j]].seed:
                    continue
                if j < i:
                    before = True
                else:
                    after = True
            if before and after:
                continue    # between drawn neighbours: no room to move
            direction = -1 if after else 1
            for _ in range(len(routes) + 1):
                # a bend in a drawn band draws its line along the band
                f0 = g.band_lo[layer] if band else v.flow - v.flow_size / 2.0
                f1 = g.band_hi[layer] if band else v.flow + v.flow_size / 2.0
                c0 = v.cross - v.before - o.padding
                c1 = v.cross + v.after + o.padding
                to = v.cross
                hit = False
                for route in routes:
                    for k in range(len(route) - 1):
                        if not _segment_in_box(route[k], route[k + 1], f0, f1,
                                               c0, c1):
                            continue
                        lo, hi = _segment_cross(route[k], route[k + 1], f0,
                                                f1)
                        if direction > 0 and hi + o.padding + v.before > to:
                            to = hi + o.padding + v.before
                        if direction < 0 and lo - o.padding - v.after < to:
                            to = lo - o.padding - v.after
                        hit = True
                if not hit or abs(to - v.cross) < COORD_EPS:
                    break
                v.cross = to
            if direction > 0:
                for j in range(i + 1, len(nodes)):
                    p = g.vertices[nodes[j - 1]]
                    q = g.vertices[nodes[j]]
                    least = p.cross + p.after + \
                        _gap(g, o, nodes[j - 1], nodes[j]) + q.before
                    if q.cross < least:
                        q.cross = least
            else:
                for j in range(i - 1, -1, -1):
                    p = g.vertices[nodes[j]]
                    q = g.vertices[nodes[j + 1]]
                    most = q.cross - q.before - \
                        _gap(g, o, nodes[j], nodes[j + 1]) - p.after
                    if p.cross > most:
                        p.cross = most


def _normalise(g: Graph) -> Tuple[float, float]:
    """Move the placed content to the origin; return its extents."""
    f0 = f1 = c0 = c1 = 0.0
    any_ = False
    for vx in g.vertices:
        if vx.kind == VERTEX_VIRTUAL:
            continue
        fa = vx.flow - vx.flow_size / 2.0
        fb = vx.flow + vx.flow_size / 2.0
        ca = vx.cross - vx.before
        cb = vx.cross + vx.after
        if not any_ or fa < f0:
            f0 = fa
        if not any_ or fb > f1:
            f1 = fb
        if not any_ or ca < c0:
            c0 = ca
        if not any_ or cb > c1:
            c1 = cb
        any_ = True
    for vx in g.vertices:
        vx.flow -= f0
        vx.cross -= c0
    for layer in range(len(g.band_drawn)):
        g.band_lo[layer] -= f0
        g.band_hi[layer] -= f0
    return (f1 - f0 if any_ else 0.0), (c1 - c0 if any_ else 0.0)


def _apply_graph(ctx: Context, ci: int, g: Graph) -> None:
    """Place the children and record the edge pieces."""
    c = ctx.containers[ci]
    o = ctx.opts
    for vx in g.vertices:
        if vx.kind != VERTEX_REAL:
            continue
        x, y = _to_doc(g.direction, vx.flow, vx.cross)
        node = vx.node
        assert node is not None
        if node.rect is not None:
            shift_subtree(node, x - node.rect.width / 2.0 - node.rect.x,
                          y - node.rect.height / 2.0 - node.rect.y)
        else:
            if node.point is None:
                node.point = Point()
            node.point.x = x
            node.point.y = y
    for e in g.edges:
        piece = Piece(e.edge)
        for i in range(1, len(e.chain) - 1):
            d = g.vertices[e.chain[i]]
            if d.kind == VERTEX_LABEL_DUMMY:
                # the line runs through the anchor, the label after it
                piece.has_label = True
                if g.direction == FLOW_DOWN:
                    piece.label.x = d.cross + o.padding / 2.0
                    piece.label.y = d.flow - e.label_h / 2.0
                else:
                    piece.label.x = d.flow - e.label_w / 2.0
                    piece.label.y = d.cross + o.padding / 2.0
                piece.label.width = e.label_w
                piece.label.height = e.label_h
            if d.layer < len(g.band_drawn) and g.band_drawn[d.layer]:
                # the update: in a drawn band the line runs along the band
                piece.bends.append(Point(*_to_doc(g.direction,
                                                  g.band_lo[d.layer],
                                                  d.cross)))
                piece.bends.append(Point(*_to_doc(g.direction,
                                                  g.band_hi[d.layer],
                                                  d.cross)))
                continue
            piece.bends.append(Point(*_to_doc(g.direction, d.flow, d.cross)))
        if e.reversed:
            piece.bends.reverse()
        c.pieces.append(piece)


def _graph_prepare(ctx: Context, ci: int) -> Graph:
    """P2 - P5: the direction-independent phases."""
    g = _build_graph(ctx, ci)
    for vx in g.vertices:
        if not vx.seed:
            continue
        if g.direction == FLOW_DOWN:
            vx.seed_flow, vx.seed_cross = vx.seed_y, vx.seed_x
        else:
            vx.seed_flow, vx.seed_cross = vx.seed_x, vx.seed_y
    if g.update:
        # a new edge inside one band keeps a straight line
        _seed_bands(g)
        g.edges = [e for e in g.edges
                   if not (e.drawn_ends and
                           g.vertices[e.source].seed_layer ==
                           g.vertices[e.target].seed_layer)]
    topo = _break_cycles(g)
    _assign_layers(g, topo)
    _insert_dummies(g, ctx.opts)
    _order(g, ctx.opts)
    return g


def _graph_frame(ctx: Context, ci: int, base: Graph,
                 direction: int) -> Tuple[Graph, float, float]:
    """P6 in one frame; the content extents in the document axes."""
    o = ctx.opts
    g = _graph_copy(base)
    g.direction = direction
    for vx in g.vertices:
        if vx.seed:
            if direction == FLOW_DOWN:
                vx.seed_flow, vx.seed_cross = vx.seed_y, vx.seed_x
            else:
                vx.seed_flow, vx.seed_cross = vx.seed_x, vx.seed_y
        if vx.kind == VERTEX_REAL and vx.node is not None and \
                vx.node.rect is not None:
            vx.flow_size, vx.cross_size = _size_to_frame(
                direction, vx.node.rect.width, vx.node.rect.height)
            vx.before = vx.after = vx.cross_size / 2.0
        elif vx.kind == VERTEX_LABEL_DUMMY and vx.edge >= 0:
            e = g.edges[vx.edge]
            if direction == FLOW_DOWN:
                vx.flow_size, cs = e.label_h, e.label_w
            else:
                vx.flow_size, cs = e.label_w, e.label_h
            vx.before = o.padding / 2.0
            vx.after = cs + o.padding / 2.0
            vx.cross_size = vx.before + vx.after
    _assign_coordinates(g, o)
    if g.update:
        _clear_routes(ctx, ci, g)
    flow_extent, cross_extent = _normalise(g)
    if direction == FLOW_DOWN:
        return g, cross_extent, flow_extent
    return g, flow_extent, cross_extent


def _graph(ctx: Context, ci: int, direction: int) -> Tuple[float, float]:
    """Lay the graph out in the frame, or the chosen one (direction < 0)."""
    base = _graph_prepare(ctx, ci)
    if direction >= 0:
        chosen = direction
    elif ctx.opts.mode == LAYOUT_ADAPTIVE and not ctx.update:
        preferred = ctx.containers[ci].direction
        _, wd, hd = _graph_frame(ctx, ci, base, FLOW_DOWN)
        _, wr, hr = _graph_frame(ctx, ci, base, FLOW_RIGHT)
        chosen = _choose(wd, hd, wr, hr, _target(ctx.opts, preferred),
                         preferred)
    else:
        chosen = ctx.containers[ci].direction
    g, content_w, content_h = _graph_frame(ctx, ci, base, chosen)
    ctx.containers[ci].direction = chosen
    _apply_graph(ctx, ci, g)
    return content_w, content_h


def _graph_extents(ctx: Context, ci: int,
                   direction: int) -> Tuple[float, float]:
    base = _graph_prepare(ctx, ci)
    _, cw, ch = _graph_frame(ctx, ci, base, direction)
    return cw, ch


# the containers: P1, P7, P8 and the border points


def _size_leaf(ctx: Context, node: Node) -> None:
    if node.type == POINT or node.rect is not None:
        return
    node.rect = Rect(0.0, 0.0,
                     node.min_rect.width if node.min_rect is not None
                     else ctx.opts.node_width,
                     node.min_rect.height if node.min_rect is not None
                     else ctx.opts.node_height)


def _fit(ctx: Context, node: Optional[Node], cw: float,
         ch: float) -> Tuple[float, float, float, float]:
    """P8: the container rect around the content, the title on top."""
    o = ctx.opts
    has_min = node is not None and node.min_rect is not None
    min_w = node.min_rect.width if has_min else 0.0    # type: ignore
    min_h = node.min_rect.height if has_min else 0.0   # type: ignore
    title = node.min_rect.height if has_min else o.padding  # type: ignore
    if cw <= 0.0 and ch <= 0.0:
        return (min_w if min_w > o.node_width else o.node_width,
                min_h if min_h > o.node_height else o.node_height,
                o.padding, title)
    width = cw + 2 * o.padding
    if min_w > width:
        width = min_w
    height = title + o.padding + ch + o.padding
    return (width, height, o.padding + (width - 2 * o.padding - cw) / 2.0,
            title + o.padding)


def _region_size(ctx: Context, ri: int,
                 direction: int) -> Tuple[float, float]:
    cw = ch = 0.0
    if ctx.containers[ri].kind == CONTAINER_GRAPH:
        cw, ch = _graph_extents(ctx, ri, direction)
    width, height, _, _ = _fit(ctx, ctx.containers[ri].node, cw, ch)
    return width, height


def _stack_extents(ctx: Context, ci: int,
                   direction: int) -> Tuple[float, float]:
    # The regions of a composite stacked across the flow axis.
    c = ctx.containers[ci]
    along = across = 0.0
    n = 0
    assert c.node is not None
    for r in c.node.children:
        if r.type != REGION or r not in ctx.index:
            continue
        width, height = _region_size(ctx, ctx.index[r], direction)
        if direction == FLOW_DOWN:
            along += width
            if height > across:
                across = height
        else:
            along += height
            if width > across:
                across = width
        n += 1
    if n > 1:
        along += (n - 1) * ctx.opts.node_gap
    return (along, across) if direction == FLOW_DOWN else (across, along)


def _region_drawn(ctx: Context, r: Node) -> bool:
    # The update: a region is seeded itself or holds a seeded vertex.
    if r in ctx.seeds:
        return True
    return any(_is_vertex(v) and v in ctx.seeds for v in r.children)


def _regions_drawn(ctx: Context, ci: int) -> bool:
    c = ctx.containers[ci]
    if not ctx.update or c.kind != CONTAINER_REGIONS:
        return False
    assert c.node is not None
    return any(r.type == REGION and _region_drawn(ctx, r)
               for r in c.node.children)


def _union(u: Rect, r: Rect, any_: bool) -> bool:
    if not any_:
        u.x, u.y, u.width, u.height = r.x, r.y, r.width, r.height
        return True
    x2 = u.x + u.width if u.x + u.width > r.x + r.width else r.x + r.width
    y2 = u.y + u.height if u.y + u.height > r.y + r.height \
        else r.y + r.height
    if r.x < u.x:
        u.x = r.x
    if r.y < u.y:
        u.y = r.y
    u.width = x2 - u.x
    u.height = y2 - u.y
    return True


def _regions_layout(ctx: Context, ci: int) -> Tuple[float, float]:
    """P7: the regions side by side across the flow axis."""
    c = ctx.containers[ci]
    assert c.node is not None
    direction = c.direction
    max_flow = cursor = w = h = 0.0
    if ctx.opts.mode == LAYOUT_ADAPTIVE and not ctx.update:
        wd, hd = _stack_extents(ctx, ci, FLOW_DOWN)
        wr, hr = _stack_extents(ctx, ci, FLOW_RIGHT)
        direction = _choose(wd, hd, wr, hr, _target(ctx.opts, c.direction),
                            c.direction)
        c.direction = direction
    for r in c.node.children:
        if r.type != REGION:
            continue
        if r not in ctx.index:
            raise GeometryError(BAD_PARAMETER, 'unknown region')
        _finish(ctx, ctx.index[r], direction)
    if _regions_drawn(ctx, ci):
        # the drawn regions keep their places; a new region goes after them
        u = Rect()
        any_ = False
        for r in c.node.children:
            if r.type == REGION and r.rect is not None and \
                    _region_drawn(ctx, r):
                any_ = _union(u, r.rect, any_)
        for r in c.node.children:
            if r.type != REGION or r.rect is None or _region_drawn(ctx, r):
                continue
            if direction == FLOW_DOWN:
                shift_subtree(r, u.x + u.width + ctx.opts.node_gap - r.rect.x,
                              u.y - r.rect.y)
            else:
                shift_subtree(r, u.x - r.rect.x,
                              u.y + u.height + ctx.opts.node_gap - r.rect.y)
            any_ = _union(u, r.rect, any_)
        return u.width, u.height
    for r in c.node.children:
        if r.type != REGION or r.rect is None:
            continue
        f = r.rect.height if direction == FLOW_DOWN else r.rect.width
        if f > max_flow:
            max_flow = f
    for r in c.node.children:
        if r.type != REGION or r.rect is None:
            continue
        if direction == FLOW_DOWN:
            r.rect.height = max_flow
            shift_subtree(r, cursor - r.rect.x, -r.rect.y)
            cursor += r.rect.width + ctx.opts.node_gap
            if r.rect.x + r.rect.width > w:
                w = r.rect.x + r.rect.width
            h = max_flow
        else:
            r.rect.width = max_flow
            shift_subtree(r, -r.rect.x, cursor - r.rect.y)
            cursor += r.rect.height + ctx.opts.node_gap
            if r.rect.y + r.rect.height > h:
                h = r.rect.y + r.rect.height
            w = max_flow
    return w, h


def _place_border_points(ctx: Context, parent: int, node: Node) -> None:
    # The entry/exit points of a child container on its border.
    direction = ctx.containers[parent].direction
    if node is None or node.rect is None:
        return
    entries = exits = ke = kx = 0
    for p in node.children:
        if not _is_border_point(p):
            continue
        if p.role == ROLE_ENTRY_POINT:
            entries += 1
        else:
            exits += 1
    r = node.rect
    for p in node.children:
        if not _is_border_point(p):
            continue
        if ctx.update and p.point is not None:
            continue
        if p.point is None:
            p.point = Point()
        if p.role == ROLE_ENTRY_POINT:
            f = (ke + 1.0) / (entries + 1.0)
            ke += 1
            if direction == FLOW_DOWN:
                p.point.x, p.point.y = r.x + r.width * f, r.y
            else:
                p.point.x, p.point.y = r.x, r.y + r.height * f
        else:
            f = (kx + 1.0) / (exits + 1.0)
            kx += 1
            if direction == FLOW_DOWN:
                p.point.x, p.point.y = r.x + r.width * f, r.y + r.height
            else:
                p.point.x, p.point.y = r.x + r.width, r.y + r.height * f


def _layout_children(ctx: Context, ci: int) -> None:
    """P1: lay the nested containers out, size the leaves."""
    for child in _first_children(ctx, ci):
        if node_is_comment(child) or _is_border_point(child):
            continue
        if _is_container(child):
            if child not in ctx.index:
                raise GeometryError(BAD_PARAMETER, 'unknown container')
            if child.type == REGION:
                _layout_children(ctx, ctx.index[child])
            else:
                _container(ctx, ctx.index[child])
        else:
            _size_leaf(ctx, child)


def _child_centre(child: Node) -> Tuple[float, float]:
    if child.rect is not None:
        return (child.rect.x + child.rect.width / 2.0,
                child.rect.y + child.rect.height / 2.0)
    if child.point is not None:
        return child.point.x, child.point.y
    return 0.0, 0.0


def _finish(ctx: Context, ci: int, direction: int) -> None:
    """Lay the content out, fit the container, place its children."""
    cw = ch = 0.0
    is_root = ci == 0
    kind = ctx.containers[ci].kind
    if kind == CONTAINER_GRAPH:
        cw, ch = _graph(ctx, ci, direction)
    elif kind == CONTAINER_REGIONS:
        if direction >= 0:
            ctx.containers[ci].direction = direction
        cw, ch = _regions_layout(ctx, ci)
    elif direction >= 0:
        ctx.containers[ci].direction = direction
    node = ctx.containers[ci].node
    width, height, ix, iy = _fit(ctx, node, cw, ch)
    if ctx.update:
        _finish_update(ctx, ci, node, is_root, width, height, ix, iy)
        return
    for child in _first_children(ctx, ci):
        if node_is_comment(child) or _is_border_point(child):
            continue
        if _is_container(child):
            _place_border_points(ctx, ci, child)
        shift_subtree(child, ix, iy)
    for piece in ctx.containers[ci].pieces:
        for p in piece.bends:
            p.x += ix
            p.y += iy
        piece.label.x += ix
        piece.label.y += iy
    if node is not None and (not is_root or ctx.reconstruct_sm or
                             ctx.sm_had_rect):
        node.rect = Rect(0.0, 0.0, width, height)


def _finish_update(ctx: Context, ci: int, node: Optional[Node],
                   is_root: bool, width: float, height: float, ix: float,
                   iy: float) -> None:
    # The update: the content goes back to the drawing.
    c = ctx.containers[ci]
    o = ctx.opts
    fit_iy = iy
    anchored = False
    if _regions_drawn(ctx, ci):
        anchored = True
        ix = iy = 0.0
    for child in c.children:
        if anchored:
            break
        seed = _seeded(ctx, child)
        if seed is None:
            continue
        cx, cy = _child_centre(child)
        ix = seed.x - cx
        iy = seed.y - cy
        anchored = True
    if not anchored and node is not None and node.rect is not None:
        ix += node.rect.x
        iy += node.rect.y
    for child in _first_children(ctx, ci):
        if node_is_comment(child) or _is_border_point(child):
            continue
        if _is_container(child):
            _place_border_points(ctx, ci, child)
        shift_subtree(child, ix, iy)
    if node is not None and (not is_root or ctx.reconstruct_sm or
                             ctx.sm_had_rect or node.rect is not None):
        bounds = _content_bounds(ctx, ci)
        if node.rect is not None:
            # grow-only around the content with the padding
            x1 = bounds.x - o.padding
            y1 = bounds.y - o.padding
            x2 = bounds.x + bounds.width + o.padding
            y2 = bounds.y + bounds.height + o.padding
            rx2 = node.rect.x + node.rect.width
            ry2 = node.rect.y + node.rect.height
            if bounds.width > 0.0 or bounds.height > 0.0:
                if x1 < node.rect.x:
                    node.rect.x = x1
                if y1 < node.rect.y:
                    node.rect.y = y1
                if x2 > rx2:
                    rx2 = x2
                if y2 > ry2:
                    ry2 = y2
                node.rect.width = rx2 - node.rect.x
                node.rect.height = ry2 - node.rect.y
        elif not anchored:
            # nothing drawn inside: the rect of the full layout
            node.rect = Rect(0.0, 0.0, width, height)
        else:
            # a new rect around the drawn content keeps the title band
            node.rect = Rect(bounds.x - o.padding, bounds.y - fit_iy,
                             bounds.width + 2 * o.padding,
                             bounds.height + fit_iy + o.padding)
            if node.rect.width < width:
                node.rect.width = width
            if node.rect.height < height:
                node.rect.height = height
    # the pieces stay in the container frame like in the full layout
    ox, oy = _origin(ctx, ci)
    for piece in c.pieces:
        for p in piece.bends:
            p.x += ix - ox
            p.y += iy - oy
        piece.label.x += ix - ox
        piece.label.y += iy - oy
    if node is not None and node.rect is not None and node in ctx.seeds:
        # a grown container keeps its drawn corner
        ctx.seeds[node] = Point(*_child_centre(node))


def _container(ctx: Context, ci: int) -> None:
    _layout_children(ctx, ci)
    _finish(ctx, ci, -1)


# P9: the edge routing in the document coordinates


def _origin(ctx: Context, ci: int) -> Tuple[float, float]:
    node = ctx.containers[ci].node
    if node is not None and node.rect is not None:
        return node.rect.x, node.rect.y
    return 0.0, 0.0


def _find_piece(ctx: Context, ci: int, e: Edge) -> Optional[Piece]:
    for piece in ctx.containers[ci].pieces:
        if piece.edge is e:
            return piece
    return None


def _border_crossing(box: Node, px: float, py: float) -> Optional[Point]:
    # The attachment point on the border of a box toward a point.
    a = Node(1, '')
    a.rect = box.rect
    a.point = box.point
    b = Node(POINT, '')
    b.point = Point(px, py)
    e = Edge('', '', '')
    e.source = a
    e.target = b
    if not attach_edge_minimal(e):
        if a.rect is None and a.point is None:
            return None
        project_edge_to_borders(e)
    return e.source_point


class _Waypoint:
    def __init__(self, marker: bool, box: Optional[Node], p: Point,
                 leaving: bool) -> None:
        self.marker = marker    # a border of the box still to resolve
        self.box = box
        self.p = p
        self.leaving = leaving  # the marker is crossed outward


def _append_piece(ctx: Context, ci: int, e: Edge,
                  wps: List[_Waypoint]) -> None:
    piece = _find_piece(ctx, ci, e)
    if piece is None:
        return
    ox, oy = _origin(ctx, ci)
    for b in piece.bends:
        wps.append(_Waypoint(False, None, Point(b.x + ox, b.y + oy), False))


def _route_loop(ctx: Context, e: Edge) -> None:
    assert e.source is not None
    ci = _container_of(ctx, e.source)
    bottom = ci >= 0 and ctx.containers[ci].direction == FLOW_RIGHT
    r = e.source.rect
    if r is None:
        return
    reconstruct_edge_loop(e, bottom)
    if e.label_rect is not None:
        o = ctx.opts
        w = e.label_rect.width if e.label_rect.width > 0.0 else o.label_width
        h = e.label_rect.height if e.label_rect.height > 0.0 \
            else o.label_height
        e.label_rect.width = w
        e.label_rect.height = h
        if bottom:
            e.label_rect.x = r.x + r.width / 2.0 - w / 2.0
            e.label_rect.y = r.y + r.height + 2 * o.padding + o.padding / 2.0
        else:
            e.label_rect.x = r.x + r.width + 2 * o.padding + o.padding / 2.0
            e.label_rect.y = r.y + r.height / 2.0 - h / 2.0


def _route_edge(ctx: Context, e: Edge) -> None:
    assert e.source is not None and e.target is not None
    chain_s: List[int] = []
    chain_t: List[int] = []
    c_ = _container_of(ctx, e.source)
    while c_ >= 0:
        chain_s.append(c_)
        c_ = _container_of(ctx, ctx.containers[c_].node)
    c_ = _container_of(ctx, e.target)
    while c_ >= 0:
        chain_t.append(c_)
        c_ = _container_of(ctx, ctx.containers[c_].node)
    lca = -1
    for item in chain_t:
        if item in chain_s:
            lca = item
            break
    if lca < 0:
        return
    wps: List[_Waypoint] = []
    # the source side: the pieces and the borders left, innermost first
    for item in chain_s:
        if item == lca:
            break
        c = ctx.containers[item]
        _append_piece(ctx, item, e, wps)
        if _is_composite(c.node) and c.node is not e.target and \
                c.node is not None and c.node.rect is not None and \
                not (_is_border_point(e.source) and
                     e.source.parent is c.node):
            wps.append(_Waypoint(True, c.node, Point(), True))
    _append_piece(ctx, lca, e, wps)
    # the target side: the borders entered, outermost first
    below = []
    for item in chain_t:
        if item == lca:
            break
        below.append(item)
    for item in reversed(below):
        c = ctx.containers[item]
        if _is_composite(c.node) and c.node is not e.source and \
                c.node is not None and c.node.rect is not None and \
                not (_is_border_point(e.target) and
                     e.target.parent is c.node):
            wps.append(_Waypoint(True, c.node, Point(), False))
        _append_piece(ctx, item, e, wps)
    # resolve the markers: a leaving border toward the next point, an
    # entering border from the previous one
    sc = Point(*_child_centre(e.source))
    tc = Point(*_child_centre(e.target))
    for i, w in enumerate(wps):
        if not w.marker or not w.leaving:
            continue
        nxt = tc
        for j in range(i + 1, len(wps)):
            if not wps[j].marker:
                nxt = wps[j].p
                break
        assert w.box is not None
        p = _border_crossing(w.box, nxt.x, nxt.y)
        if p is not None:
            w.p = p
            w.marker = False
    for i in range(len(wps), 0, -1):
        w = wps[i - 1]
        if not w.marker or w.leaving:
            continue
        prev = sc
        for j in range(i - 1, 0, -1):
            if not wps[j - 1].marker:
                prev = wps[j - 1].p
                break
        assert w.box is not None
        p = _border_crossing(w.box, prev.x, prev.y)
        if p is not None:
            w.p = p
            w.marker = False
    wps = [w for w in wps if not w.marker]
    # the ends
    if not wps:
        if not attach_edge_minimal(e):
            project_edge_to_borders(e)
    else:
        p = _border_crossing(e.source, wps[0].p.x, wps[0].p.y)
        e.source_point = (p if p is not None else sc).copy()
        p = _border_crossing(e.target, wps[-1].p.x, wps[-1].p.y)
        e.target_point = (p if p is not None else tc).copy()
        e.polyline = [w.p.copy() for w in wps]
    # the label: the slot of the tail piece, or beside the first segment
    if e.label_rect is not None:
        o = ctx.opts
        tail = _container_of(ctx, e.source)
        piece = _find_piece(ctx, tail, e) if tail >= 0 else None
        w_ = e.label_rect.width if e.label_rect.width > 0.0 \
            else o.label_width
        h_ = e.label_rect.height if e.label_rect.height > 0.0 \
            else o.label_height
        e.label_rect.width = w_
        e.label_rect.height = h_
        if piece is not None and piece.has_label:
            ox, oy = _origin(ctx, tail)
            e.label_rect.x = piece.label.x + ox
            e.label_rect.y = piece.label.y + oy
        else:
            assert e.source_point is not None and e.target_point is not None
            a = e.source_point
            b = e.target_point if not wps else wps[0].p
            e.label_rect.x = (a.x + b.x) / 2.0 + o.padding
            e.label_rect.y = (a.y + b.y) / 2.0 - h_ / 2.0


def _same_pair(a: Edge, b: Edge) -> bool:
    return (a.source is b.source and a.target is b.target) or \
        (a.source is b.target and a.target is b.source)


def _shift_edge(e: Edge, dx: float, dy: float) -> None:
    for p in (e.source_point, e.target_point, e.label_point, e.label_rect):
        if p is not None:
            p.x += dx
            p.y += dy


def _straight(f: Edge) -> bool:
    return f.source is not None and f.target is not None and \
        f.source is not f.target and not f.polyline and \
        f.source_point is not None and f.target_point is not None


def _spread_pairs(ctx: Context) -> None:
    """Spread the coinciding straight transitions of one pair of states."""
    step = 2 * ctx.opts.padding
    for e in ctx.tree.edges:
        if not _straight(e):
            continue
        if ctx.update and e not in ctx.routed:
            continue
        group = [f for f in ctx.tree.edges
                 if _straight(f) and _same_pair(e, f) and
                 (not ctx.update or f in ctx.routed)]
        if len(group) < 2 or group[0] is not e:
            continue
        ci = _container_of(ctx, e.source)
        across_x = ci < 0 or ctx.containers[ci].direction == FLOW_DOWN
        k = 0.0
        for f in group:
            d = (k - (len(group) - 1) / 2.0) * step
            _shift_edge(f, d if across_x else 0.0, 0.0 if across_x else d)
            k += 1.0


def _edge_kept(ctx: Context, e: Edge) -> bool:
    # The update: a drawn transition stays when its ends moved alike.
    if not ctx.update or e not in ctx.edge_seeds:
        return False
    assert e.source is not None and e.target is not None
    s0 = _seeded(ctx, e.source)
    t0 = _seeded(ctx, e.target)
    if s0 is None or t0 is None:
        return False
    s1x, s1y = _child_centre(e.source)
    t1x, t1y = _child_centre(e.target)
    dx = s1x - s0.x
    dy = s1y - s0.y
    if abs(t1x - t0.x - dx) > COORD_EPS or abs(t1y - t0.y - dy) > COORD_EPS:
        return False
    if abs(dx) > COORD_EPS or abs(dy) > COORD_EPS:
        _shift_edge(e, dx, dy)
        for p in e.polyline or []:
            p.x += dx
            p.y += dy
    return True


LAYOUT_INSIDE = 1.0     # an end this far inside is not a drawing slip


def _point_inside(p: Point, r: Rect, eps: float) -> bool:
    return r.x + eps < p.x < r.x + r.width - eps and \
        r.y + eps < p.y < r.y + r.height - eps


def _fit_route_end(end: Point, nxt: Point, n: Node) -> bool:
    """Slide a kept route end inside its grown node to the border."""
    r = n.rect
    dx = nxt.x - end.x
    dy = nxt.y - end.y
    t = 1.0
    if r is None or not _point_inside(end, r, LAYOUT_INSIDE):
        return True
    if not _point_inside(nxt, r, -COORD_EPS):
        if dx > COORD_EPS:
            t = min(t, (r.x + r.width - end.x) / dx)
        if dx < -COORD_EPS:
            t = min(t, (r.x - end.x) / dx)
        if dy > COORD_EPS:
            t = min(t, (r.y + r.height - end.y) / dy)
        if dy < -COORD_EPS:
            t = min(t, (r.y - end.y) / dy)
        end.x += t * dx
        end.y += t * dy
        return True
    return False


def _is_ancestor(a: Node, n: Optional[Node]) -> bool:
    n = n.parent if n is not None else None
    while n is not None:
        if n is a:
            return True
        n = n.parent
    return False


def _fit_route(e: Edge) -> bool:
    assert e.source is not None and e.target is not None
    if _is_ancestor(e.source, e.target) or _is_ancestor(e.target, e.source):
        return True
    last = e.polyline[-1] if e.polyline else None
    if e.source_point is not None and (e.polyline or
                                       e.target_point is not None):
        nxt = e.polyline[0] if e.polyline else e.target_point
        assert nxt is not None
        if not _fit_route_end(e.source_point, nxt.copy(), e.source):
            return False
    if e.target_point is not None and (last is not None or
                                       e.source_point is not None):
        nxt = last if last is not None else e.source_point
        assert nxt is not None
        if not _fit_route_end(e.target_point, nxt.copy(), e.target):
            return False
    return True


def _drop_edge_geometry(e: Edge) -> None:
    e.source_point = e.target_point = e.label_point = None
    e.polyline = None
    if e.label_rect is not None:
        e.label_rect.x = e.label_rect.y = 0.0   # the size stays the preset


def _route_edges(ctx: Context) -> None:
    for e in ctx.tree.edges:
        if e.source is None or e.target is None or \
                node_is_comment(e.source) or node_is_comment(e.target):
            continue
        if (e.source.rect is None and e.source.point is None) or \
                (e.target.rect is None and e.target.point is None):
            continue
        if ctx.update:
            if _edge_kept(ctx, e) and _fit_route(e):
                continue
            _drop_edge_geometry(e)
            ctx.routed.add(e)
        if e.source is e.target:
            _route_loop(ctx, e)
            continue
        _route_edge(ctx, e)
    _spread_pairs(ctx)


# P10: the comments


def _rects_overlap(a: Rect, b: Rect) -> bool:
    return a.x < b.x + b.width and b.x < a.x + a.width and \
        a.y < b.y + b.height and b.y < a.y + a.height


def _node_bounds(n: Node) -> Rect:
    if n.rect is not None:
        return n.rect.copy()
    if n.point is not None:
        return Rect(n.point.x, n.point.y, 0.0, 0.0)
    return Rect()


def _rect_free(ctx: Context, ci: int, self_: Node, r: Rect) -> bool:
    # The rect is free of the container's other children.
    for n in _first_children(ctx, ci):
        if n is self_ or (n.rect is None and n.point is None):
            continue
        if _rects_overlap(r, _node_bounds(n)):
            return False
    return True


def _content_bounds(ctx: Context, ci: int) -> Rect:
    r = Rect()
    any_ = False
    for n in _first_children(ctx, ci):
        if node_is_comment(n) or (n.rect is None and n.point is None):
            continue
        b = _node_bounds(n)
        if not any_:
            r = b
            any_ = True
            continue
        x2 = r.x + r.width if r.x + r.width > b.x + b.width \
            else b.x + b.width
        y2 = r.y + r.height if r.y + r.height > b.y + b.height \
            else b.y + b.height
        if b.x < r.x:
            r.x = b.x
        if b.y < r.y:
            r.y = b.y
        r.width = x2 - r.x
        r.height = y2 - r.y
    return r


def _place_comment(ctx: Context, comment: Node) -> None:
    o = ctx.opts
    if comment.rect is not None:
        return
    r = Rect(0.0, 0.0,
             comment.min_rect.width if comment.min_rect is not None
             else o.node_width,
             comment.min_rect.height if comment.min_rect is not None
             else o.node_height)
    element = None
    for edge in ctx.tree.edges:
        if edge.source is comment and edge.target is not None and \
                edge.target is not comment:
            element = edge.target
            break
    if element is not None and (element.rect is not None or
                                element.point is not None):
        ci = _container_of(ctx, element)
        direction = ctx.containers[ci].direction if ci >= 0 \
            else o.direction
        gap = o.node_gap
        e = _node_bounds(element)
        for cand in range(3):
            if ci < 0:
                break
            if direction == FLOW_DOWN:
                if cand == 0:
                    r.x, r.y = e.x + e.width + gap, e.y
                elif cand == 1:
                    r.x, r.y = e.x - gap - r.width, e.y
                else:
                    r.x, r.y = e.x, e.y + e.height + gap
            else:
                if cand == 0:
                    r.x, r.y = e.x, e.y + e.height + gap
                elif cand == 1:
                    r.x, r.y = e.x, e.y - gap - r.height
                else:
                    r.x, r.y = e.x + e.width + gap, e.y
            if _rect_free(ctx, ci, comment, r):
                comment.rect = r.copy()
                return
    # the shelf after the content of the comment's own container
    ci = _container_of(ctx, comment)
    if ci < 0:
        ci = 0
    content = _content_bounds(ctx, ci)
    c = ctx.containers[ci]
    if c.direction == FLOW_DOWN:
        r.x = content.x + c.shelf
        r.y = content.y + content.height + o.node_gap
        c.shelf += r.width + o.node_gap
    else:
        r.x = content.x + content.width + o.node_gap
        r.y = content.y + c.shelf
        c.shelf += r.height + o.node_gap
    comment.rect = r.copy()


def _place_comments(ctx: Context, nodes: List[Node]) -> None:
    for n in nodes:
        if node_is_comment(n):
            _place_comment(ctx, n)
        if n.children:
            _place_comments(ctx, n.children)


# the tree layout


def _final_shape(ctx: Context) -> Tuple[float, float]:
    # The machine shape: the root rect, else the top-level content.
    root = ctx.containers[0].node
    if root is not None and root.rect is not None:
        return root.rect.width, root.rect.height
    r = _content_bounds(ctx, 0)
    return r.width, r.height


def _collect_seeds(ctx: Context, nodes: List[Node]) -> None:
    for n in nodes:
        if n.rect is not None or n.point is not None:
            ctx.seeds[n] = Point(*_child_centre(n))
        if n.children:
            _collect_seeds(ctx, n.children)


def _tree_pass(tree: Tree, reconstruct_sm: bool, opts: LayoutOptions,
               start: int, update: bool) -> Tuple[float, float]:
    from .transform import grow_sm_border
    ctx = Context(tree, opts, start, reconstruct_sm, update)
    root = tree.nodes[0] if len(tree.nodes) == 1 and \
        tree.nodes[0].type == TREE else None
    ctx.sm_had_rect = root is not None and root.rect is not None
    if update:
        _collect_seeds(ctx, tree.nodes)
        for e in tree.edges:
            if e.source_point is not None or e.target_point is not None or \
                    e.polyline is not None or e.label_point is not None:
                ctx.edge_seeds.add(e)
    else:
        clean_tree_geometry(tree.nodes)
        for e in tree.edges:
            e.source_point = e.target_point = e.label_point = None
            e.polyline = None
    _collect(ctx, root, 0)
    _seed_edges(ctx)
    if update:
        _infer_directions(ctx)
    _container(ctx, 0)
    _route_edges(ctx)
    _place_comments(ctx, tree.nodes)
    grow_sm_border(tree)
    return _final_shape(ctx)


def layout_tree(tree: Tree, reconstruct_sm: bool, opts: LayoutOptions,
                update: bool) -> None:
    """Lay a tree out; the adaptive mode keeps the better of two starts."""
    if update or opts.mode != LAYOUT_ADAPTIVE:
        _tree_pass(tree, reconstruct_sm, opts, opts.direction, update)
        return
    wr, hr = _tree_pass(tree, reconstruct_sm, opts, FLOW_RIGHT, False)
    wd, hd = _tree_pass(tree, reconstruct_sm, opts, FLOW_DOWN, False)
    better = _shape_better(wr, hr, wd, hd, opts.aspect)
    if better == 0 or (better < 0 and opts.direction == FLOW_RIGHT):
        _tree_pass(tree, reconstruct_sm, opts, FLOW_RIGHT, False)


def _shift_tree(tree: Tree, dx: float, dy: float) -> None:
    for n in tree.nodes:
        shift_subtree(n, dx, dy)
    for e in tree.edges:
        _shift_edge(e, dx, dy)
        for p in e.polyline or []:
            p.x += dx
            p.y += dy


def place_trees(trees: List[Tree], opts: LayoutOptions,
                drawn: Optional[List[bool]]) -> None:
    """Place the machines in a row; the drawn ones keep their place."""
    cursor = 0.0
    for k, tree in enumerate(trees):
        if not drawn or not drawn[k]:
            continue
        b = tree_bounding_rect(tree, False)
        if b.x + b.width + 2 * opts.node_gap > cursor:
            cursor = b.x + b.width + 2 * opts.node_gap
    for k, tree in enumerate(trees):
        if drawn and drawn[k]:
            continue
        b = tree_bounding_rect(tree, False)
        _shift_tree(tree, cursor - b.x, -b.y)
        cursor += b.width + 2 * opts.node_gap
