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
import heapq
import math
from typing import Dict, List, Optional, Set, Tuple

from .transform import (attach_edge_minimal, clean_tree_geometry,
                        node_is_comment, project_edge_to_borders,
                        reconstruct_edge_loop, shift_subtree,
                        tree_bounding_rect)
from .types import (BAD_PARAMETER, CHOICE_SIZE, COMMENT, COMPOSITE,
                    COORD_EPS, FLOW_DOWN, FLOW_RIGHT, LABEL_HEIGHT,
                    LABEL_WIDTH, LAYER_GAP,
                    LAYOUT_ADAPTIVE, LAYOUT_ALTERNATE, LAYOUT_ASPECT,
                    LAYOUT_FIXED, LAYOUT_SWEEPS, NODE_GAP, NODE_HEIGHT,
                    NODE_WIDTH, PADDING, POINT, POINT_SIZE, REGION,
                    CHANNEL_GAP, ROUTING_ORTHOGONAL, ROUTING_POLYLINE,
                    SEED_ALIGN, SEED_PULL, SEED_PULL_STRETCH,
                    ROLE_CHOICE, ROLE_DEEP_HISTORY, ROLE_ENTRY_POINT,
                    ROLE_EXIT_POINT,
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
                          ('choice_size', CHOICE_SIZE),
                          ('label_width', LABEL_WIDTH),
                          ('label_height', LABEL_HEIGHT)):
        if getattr(out, name) <= 0:
            setattr(out, name, default)
    if out.seed_pull < 0.0:
        out.seed_pull = SEED_PULL     # 0: the order alone
    if out.routing != ROUTING_ORTHOGONAL:
        out.routing = ROUTING_POLYLINE
    return out


# the layered layout anew, seeded and pinned by the existing geometry (the
# update), or seeded by it (the arrange)
REBUILD_FULL = 0
REBUILD_UPDATE = 1
REBUILD_ARRANGE = 2


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
        self.seed = False           # the seeded layout: it had geometry
        self.seed_x = 0.0           # its centre in the document
        self.seed_y = 0.0
        self.seed_flow = 0.0        # its centre in the frame
        self.seed_cross = 0.0
        self.seed_layer = 0         # its band among the seeded vertices, 1..
        self.seed_w = 0.0           # its extent in the seed
        self.seed_h = 0.0
        self.seed_flow_size = 0.0   # its extent along the flow of the frame
        self.pulled = False         # the arrange: it aims at its seed place
        self.pull_target = 0.0      # that place across the flow, in the layout


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
        self.seeded_ends = False    # both ends seeded (or outside)
        self.drawn_ends = False     # the update: between two pinned vertices
        self.chain: List[int] = []  # source, dummies, target by layer
        # the orthogonal routing: the ends across the flow, off the centres of
        # the end vertices; the channel in the gap after each step, 0 straight
        self.port_s = 0.0
        self.port_t = 0.0
        self.channel: List[int] = []
        # the source, the target: a composite end whose inner run crosses its
        # border at a point off its centre, its inner flow running so
        self.inner: List[Optional[Point]] = [None, None]
        self.inner_dir = [0, 0]


class Graph:
    """The layout graph of one container."""

    def __init__(self) -> None:
        self.direction = FLOW_RIGHT
        self.seeded = False                # the bands and the seed order
        self.pinned = False                # the update: the seeded places kept
        self.pull = 0.0                    # the arrange: the seed_pull
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
        self.orthogonal = False            # the routes along and across
        self.channels: List[int] = []      # the channels of the gap after
        self.gaps: List[float] = []        # the gap after a layer


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
        self.boxes: List[Optional[Node]] = []  # orthogonal: the port nodes
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
                 reconstruct_sm: bool, mode: int) -> None:
        self.tree = tree
        self.opts = opts
        self.start = start              # the root frame of this pass
        self.reconstruct_sm = reconstruct_sm
        self.sm_had_rect = False
        self.seeded = mode != REBUILD_FULL   # the geometry is the seed
        self.pinned = mode == REBUILD_UPDATE  # the update: the seed is kept
        self.containers: List[Container] = []   # pre-order, 0 = the root
        self.index: Dict[Node, int] = {}
        self.seeds: Dict[Node, Point] = {}      # the centres before
        self.seed_sizes: Dict[Node, Rect] = {}  # the arrange: the minimums
        self.edge_seeds: Set[Edge] = set()      # the edges with geometry
        self.routed: Set[Edge] = set()          # routed in this pass


def _seeded(ctx: Context, node: Node) -> Optional[Point]:
    return ctx.seeds.get(node)


def _at_least_seed(ctx: Context, n: Optional[Node], w: float,
                   h: float) -> Tuple[float, float]:
    # The arrange: a seeded node is at least its seed rect.
    seed = ctx.seed_sizes.get(n) if n is not None else None
    if seed is None:
        return w, h
    return (seed.width if seed.width > w else w,
            seed.height if seed.height > h else h)


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


def _count_spread(ctx: Context, ci: int) -> Tuple[int, int]:
    # The arrange: a container without seeded transitions runs along the
    # axis its seeded children spread along.
    c = ctx.containers[ci]
    if c.kind != CONTAINER_GRAPH:
        return 0, 0
    xs, ys = [], []
    for child in c.children:
        p = _seeded(ctx, child)
        if p is not None:
            xs.append(p.x)
            ys.append(p.y)
    if not xs:
        return 0, 0
    wide, tall = max(xs) - min(xs), max(ys) - min(ys)
    if wide > tall + COORD_EPS:
        return 1, 0
    if tall > wide + COORD_EPS:
        return 0, 1
    return 0, 0


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
        if right == down and not ctx.pinned:
            r, d = _count_spread(ctx, ci)
            right += r
            down += d
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


def _inner_end(ctx: Context, child: Node, end: Optional[Node], edge: Edge,
               leaving: bool) -> Optional[Tuple[Point, int]]:
    # The orthogonal routing: where the inner run of an edge crosses the
    # border of the composite child holding its end, off the child's centre
    # - the last point of the inner piece of a leaving edge, the first of an
    # entering one, in the composite's own graph or in its region's.
    if child is end or child.rect is None or child not in ctx.index:
        return None
    ci = ctx.index[child]
    box = child
    piece = _find_piece(ctx, ci, edge)
    for r in child.children:
        if piece is not None:
            break
        if r.type != REGION or r.rect is None or r not in ctx.index:
            continue
        piece = _find_piece(ctx, ctx.index[r], edge)
        if piece is not None:
            box = r
            ci = ctx.index[r]
    if piece is None or not piece.bends:
        return None
    b = piece.bends[-1] if leaving else piece.bends[0]
    assert box.rect is not None
    at = Point(b.x + box.rect.x - child.rect.x - child.rect.width / 2.0,
               b.y + box.rect.y - child.rect.y - child.rect.height / 2.0)
    return at, ctx.containers[ci].direction


def _build_graph(ctx: Context, ci: int) -> Graph:
    c = ctx.containers[ci]
    o = ctx.opts
    n = len(c.children)
    g = Graph()
    g.direction = c.direction
    g.seeded = ctx.seeded
    g.pinned = ctx.pinned
    g.pull = o.seed_pull if ctx.seeded and not ctx.pinned else 0.0
    g.orthogonal = o.routing == ROUTING_ORTHOGONAL
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
        if ctx.seeded:
            centre = _seeded(ctx, node)
            if centre is not None:
                # the bands are read in the seed's own extents: the arrange
                # seed has its own scale, the update seed is the drawing
                size = ctx.seed_sizes.get(node)
                v.seed = True
                v.seed_x = centre.x
                v.seed_y = centre.y
                if size is not None:
                    v.seed_w, v.seed_h = size.width, size.height
                elif node.rect is not None:
                    v.seed_w, v.seed_h = node.rect.width, node.rect.height
                else:
                    v.seed_w = v.seed_h = o.point_size
        if node.rect is not None:
            v.flow_size, v.cross_size = _size_to_frame(
                c.direction, node.rect.width, node.rect.height)
        else:
            v.flow_size = v.cross_size = o.point_size
        v.before = v.after = v.cross_size / 2.0
    for s in c.seeds:
        if s.self_loop:
            continue
        seeded_ends = ctx.seeded and \
            (s.source_child < 0 or g.vertices[s.source_child + 1].seed) and \
            (s.target_child < 0 or g.vertices[s.target_child + 1].seed)
        drawn_ends = seeded_ends and ctx.pinned
        if drawn_ends and (s.source_child < 0 or s.target_child < 0 or
                           s.edge in ctx.edge_seeds):
            # a drawn transition between drawn elements keeps its geometry
            continue
        e = LayoutEdge(g.entry if s.source_child < 0 else s.source_child + 1,
                       g.exit if s.target_child < 0 else s.target_child + 1,
                       s.edge)
        e.seeded_ends = seeded_ends
        e.drawn_ends = drawn_ends
        if o.routing == ROUTING_ORTHOGONAL:
            for k, (child, end, leaving) in enumerate((
                    (s.source_child, s.edge.source, True),
                    (s.target_child, s.edge.target, False))):
                if child >= 0:
                    found = _inner_end(ctx, c.children[child], end, s.edge,
                                       leaving)
                    if found is not None:
                        e.inner[k], e.inner_dir[k] = found
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
    e.inner.reverse()
    e.inner_dir.reverse()
    e.reversed = not e.reversed


def _break_cycles(g: Graph) -> List[int]:
    """P2: reverse the back edges; return the topological order."""
    n = len(g.vertices)
    for e in g.edges:
        sv = g.vertices[e.source]
        tv = g.vertices[e.target]
        if g.seeded and sv.seed and tv.seed:
            # the drawing decides: a transition running backward
            if tv.seed_flow < sv.seed_flow - COORD_EPS:
                _reverse_edge(e)
            continue
        if g.seeded and (sv.seed or tv.seed):
            continue    # the roles of the drawn vertices stay drawn
        if (_source_role(tv.role) and e.source != g.entry) or \
                (_sink_role(sv.role) and e.target != g.exit):
            _reverse_edge(e)
    bands = 0
    node_of = list(range(n))
    for v in range(n):
        vx = g.vertices[v]
        if g.seeded and vx.seed and vx.seed_layer > 0:
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
            order.append((vx.seed_flow - vx.seed_flow_size / 2.0, v))
    order.sort()
    band_end = 0.0
    band = 0
    for start, v in order:
        vx = g.vertices[v]
        end = vx.seed_flow + vx.seed_flow_size / 2.0
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
                     not (g.seeded and g.vertices[v].seed)
                     for v in range(1, n))
    bands = 0
    if g.seeded:
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
        if not g.seeded:
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
        if _sink_role(vx.role) and not (g.seeded and vx.seed):
            if vx.layer > sink_layer:
                sink_layer = vx.layer
        elif vx.layer > max_layer:
            max_layer = vx.layer
    if 0 < sink_layer < max_layer + 1:
        sink_layer = max_layer + 1
    for v in range(1, n - 1):
        vx = g.vertices[v]
        if _sink_role(vx.role) and not (g.seeded and vx.seed):
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
    if g.seeded:
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
        if not nb or (g.seeded and g.vertices[v].seed):
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
    result.seeded = g.seeded
    result.pinned = g.pinned
    result.pull = g.pull
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
        copy_e.channel = list(e.channel)
        copy_e.inner = list(e.inner)
        copy_e.inner_dir = list(e.inner_dir)
        result.edges.append(copy_e)
    result.layers = [list(layer) for layer in g.layers]
    result.up = [list(x) for x in g.up]
    result.down = [list(x) for x in g.down]
    result.entry, result.exit, result.last = g.entry, g.exit, g.last
    result.band_lo = list(g.band_lo)
    result.band_hi = list(g.band_hi)
    result.band_drawn = list(g.band_drawn)
    result.orthogonal = g.orthogonal
    result.channels = list(g.channels)
    result.gaps = list(g.gaps)
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
            drawn = g.seeded and g.vertices[nodes[i]].seed
            while j < len(nodes) and abs(b[j] - b[i]) < COORD_EPS:
                if g.seeded and g.vertices[nodes[j]].seed:
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
    if g.pinned and g.vertices[u].seed and g.vertices[v].seed:
        return 0.0      # the drawn neighbours keep their drawn gap
    return o.node_gap


def _aim(g: Graph, v: Vertex) -> Optional[float]:
    # The place across the flow a vertex is held at: a drawn vertex of the
    # update, a seeded vertex of the arrange with the pull.
    if g.pinned and v.seed:
        return v.seed_cross
    if not g.pinned and v.pulled:
        return v.pull_target
    return None


def _pack_layer(g: Graph, o: LayoutOptions, layer: int) -> None:
    nodes = g.layers[layer]
    pos = 0.0
    for i, w in enumerate(nodes):
        v = g.vertices[w]
        if i > 0:
            pos += _gap(g, o, nodes[i - 1], w) + v.before
        else:
            pos = v.before
        aim = _aim(g, v)
        if aim is not None and aim > pos:
            pos = aim
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
        aim = _aim(g, v)
        if aim is not None:
            # a drawn or pulled vertex aims at its place above every pull
            d[i] = aim
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
        drawn = _aim(g, g.vertices[nodes[i]]) is not None
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


def _band_centres(g: Graph, o: LayoutOptions) -> List[float]:
    # The centres of the bands of the layers a layer gap apart.
    start = 0.0
    centre = [0.0] * (g.last + 2)
    for layer in range(1, g.last + 1):
        band = 0.0
        for w in g.layers[layer]:
            if g.vertices[w].flow_size > band:
                band = g.vertices[w].flow_size
        centre[layer] = start + band / 2.0
        start += band + o.layer_gap
    return centre


def _seed_flow(g: Graph, layer: int) -> Optional[float]:
    # The mean seed place along the flow of the seeded vertices of a layer.
    total = 0.0
    n = 0
    for w in g.layers[layer]:
        v = g.vertices[w]
        if v.kind == VERTEX_REAL and v.seed:
            total += v.seed_flow
            n += 1
    return total / n if n else None


def _seed_ratios(g: Graph, o: LayoutOptions,
                 centre: List[float]) -> List[float]:
    # The ratios of the least distances of the layout to the seed distances:
    # the consecutive seeded vertices of a layer across the flow (with all
    # the vertices between), the consecutive seeded bands along it.
    ratios: List[float] = []
    prev = -1
    prev_flow = 0.0
    for layer in range(1, g.last + 1):
        nodes = g.layers[layer]
        need = 0.0
        last = -1
        for i, w in enumerate(nodes):
            v = g.vertices[w]
            if i > 0:
                need += g.vertices[nodes[i - 1]].after + \
                    _gap(g, o, nodes[i - 1], w) + v.before
            if v.kind != VERTEX_REAL or not v.seed:
                continue
            if last >= 0:
                gap = v.seed_cross - g.vertices[nodes[last]].seed_cross
                if gap > COORD_EPS:
                    ratios.append(need / gap)
            last = i
            need = 0.0
        flow = _seed_flow(g, layer)
        if flow is None:
            continue
        if prev >= 1 and flow - prev_flow > COORD_EPS:
            ratios.append((centre[layer] - centre[prev]) / (flow - prev_flow))
        prev = layer
        prev_flow = flow
    return ratios


def _pull_targets(g: Graph, o: LayoutOptions, centre: List[float]) -> float:
    # The arrange: the seed scaled to the least distances of the layout -
    # the largest ratio, at most SEED_PULL_STRETCH times the median (the
    # rough boxes), the seed never pressed; the seeded vertices aim at their
    # scaled places across the flow, centred on the layout without the pull,
    # the share seed_pull of the way; the vertices drawn in line (SEED_ALIGN,
    # one per layer) aim at the mean of their line. The scale, 0 when the
    # seed gives none.
    ratios = sorted(_seed_ratios(g, o, centre))
    if not ratios:
        return 0.0
    share = g.pull if g.pull < 1.0 else 1.0
    median = ratios[len(ratios) // 2]
    scale = ratios[-1] if ratios[-1] < SEED_PULL_STRETCH * median \
        else SEED_PULL_STRETCH * median
    if scale < 1.0:
        scale = 1.0
    seeded = [k for k, v in enumerate(g.vertices)
              if v.kind == VERTEX_REAL and v.seed and v.layer >= 1]
    if not seeded:
        return 0.0
    sc = c = 0.0
    for k in seeded:
        sc += g.vertices[k].seed_cross
        c += g.vertices[k].cross
    sc /= len(seeded)
    c /= len(seeded)
    line = sorted((g.vertices[k].seed_cross, k) for k in seeded)
    first = 0
    for i in range(1, len(line) + 1):
        if i < len(line):
            p = g.vertices[line[i - 1][1]]
            v = g.vertices[line[i][1]]
            extent = p.cross_size if p.cross_size > v.cross_size \
                else v.cross_size
            join = scale * (v.seed_cross - p.seed_cross) < SEED_ALIGN * extent
            if join and any(g.vertices[line[j][1]].layer == v.layer
                            for j in range(first, i)):
                join = False
            if join:
                continue
        mean = 0.0
        for j in range(first, i):
            mean += line[j][0]
        mean /= float(i - first)
        for j in range(first, i):
            v = g.vertices[line[j][1]]
            v.pulled = True
            v.pull_target = v.cross + \
                share * (c + scale * (mean - sc) - v.cross)
        first = i
    return scale


def _node_frame(g: Graph, v: Vertex) -> Tuple[float, float]:
    # The orthogonal routing: the extents of the node of a real vertex in
    # the frame, 0 for a point.
    if v.kind == VERTEX_REAL and v.node is not None and \
            v.node.rect is not None:
        return _size_to_frame(g.direction, v.node.rect.width,
                              v.node.rect.height)
    return 0.0, 0.0


def _chain_cross(g: Graph, e: LayoutEdge, i: int) -> float:
    # The cross of a point of a chain: the port of a real end, the line of
    # a dummy, the next point's for an end outside the container.
    m = len(e.chain) - 1
    v = g.vertices[e.chain[i]]
    if v.kind == VERTEX_VIRTUAL and m >= 1:
        j = 1 if i == 0 else m - 1
        if g.vertices[e.chain[j]].kind != VERTEX_VIRTUAL:
            return _chain_cross(g, e, j)
    if v.kind == VERTEX_REAL and i == 0:
        return v.cross + e.port_s
    if v.kind == VERTEX_REAL and i == m:
        return v.cross + e.port_t
    return v.cross


def _inner_port(g: Graph, e: LayoutEdge, side: int) -> bool:
    # An end inside a composite takes the place of its inner run when that
    # run crosses the side of the port: the inner flow runs as the outer one
    # and the edge goes with it.
    return e.inner[side] is not None and not e.reversed and \
        e.inner_dir[side] == g.direction


def _ports(g: Graph) -> None:
    # The ports: the ends of a real vertex spread evenly along its side
    # facing the next layer (the outgoing) and the previous one (the
    # incoming), in the order of the other point of their step; a choice
    # ends at its tips and a point at itself, the centre.
    out: List[List[Tuple[float, int]]] = [[] for _ in g.vertices]
    in_: List[List[Tuple[float, int]]] = [[] for _ in g.vertices]
    for k, e in enumerate(g.edges):
        m = len(e.chain) - 1
        e.port_s = e.port_t = 0.0
        e.channel = [0] * m
        if m < 1:
            continue
        out[e.chain[0]].append((g.vertices[e.chain[1]].cross, k))
        in_[e.chain[m]].append((g.vertices[e.chain[m - 1]].cross, k))
    for v, vx in enumerate(g.vertices):
        if vx.kind != VERTEX_REAL:
            continue
        _, cs = _node_frame(g, vx)
        if vx.role == ROLE_CHOICE or cs <= 0.0:
            continue
        for side in (0, 1):
            ends = sorted(in_[v] if side else out[v])
            free = sum(1 for _, k in ends
                       if not _inner_port(g, g.edges[k], side))
            j = 0
            for _, k in ends:
                e = g.edges[k]
                inner = e.inner[side]
                if _inner_port(g, e, side) and inner is not None:
                    at = inner.x if g.direction == FLOW_DOWN else inner.y
                    at = min(max(at, -cs / 2.0), cs / 2.0)
                else:
                    at = -cs / 2.0 + cs * float(j + 1) / float(free + 1)
                    j += 1
                if side:
                    e.port_t = at
                else:
                    e.port_s = at


def _dummy_fits(g: Graph, o: LayoutOptions, d: int, cross: float) -> bool:
    # A dummy at a cross keeps the order and the gaps of its layer.
    v = g.vertices[d]
    nodes = g.layers[v.layer]
    i = v.order
    if i >= len(nodes) or nodes[i] != d:
        if d not in nodes:
            return False
        i = nodes.index(d)
    if i > 0:
        lv = g.vertices[nodes[i - 1]]
        if lv.cross + lv.after + _gap(g, o, nodes[i - 1], d) + v.before > \
                cross + COORD_EPS:
            return False
    if i + 1 < len(nodes):
        rv = g.vertices[nodes[i + 1]]
        if cross + v.after + _gap(g, o, d, nodes[i + 1]) + rv.before > \
                rv.cross + COORD_EPS:
            return False
    return True


def _straighten(g: Graph, o: LayoutOptions) -> None:
    # The dummies of a chain on the line of a port: they move onto the line
    # of the source port, else of the target port, where every layer has
    # room - the chain runs straight from its end.
    for e in g.edges:
        m = len(e.chain) - 1
        if m < 2:
            continue
        aims = []
        if g.vertices[e.chain[0]].kind == VERTEX_REAL:
            aims.append(_chain_cross(g, e, 0))
        if g.vertices[e.chain[m]].kind == VERTEX_REAL:
            aims.append(_chain_cross(g, e, m))
        for aim in aims:
            if all(abs(g.vertices[e.chain[i]].cross - aim) <= COORD_EPS
                   for i in range(1, m)):
                break
            if not all(_dummy_fits(g, o, e.chain[i], aim)
                       for i in range(1, m)):
                continue
            for i in range(1, m):
                g.vertices[e.chain[i]].cross = aim
            break


class _Step:
    """A step across the flow in a gap."""

    def __init__(self, edge: int, step: int, a: float, b: float) -> None:
        self.edge = edge
        self.step = step
        self.a = a
        self.b = b
        self.group = -1


class _ChannelGroup:
    def __init__(self, lo: float, hi: float) -> None:
        self.lo = lo
        self.hi = hi
        self.starts: List[float] = []
        self.ends: List[float] = []


def _strictly_in(x: float, lo: float, hi: float) -> bool:
    return lo + COORD_EPS < x < hi - COORD_EPS


def _channel_cost(s: _ChannelGroup, t: _ChannelGroup) -> int:
    # The crossings when the group s runs nearer the layer before than t.
    return sum(1 for a in t.starts if _strictly_in(a, s.lo, s.hi)) + \
        sum(1 for b in s.ends if _strictly_in(b, t.lo, t.hi))


def _group_root(parent: List[int], x: int) -> int:
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def _channels(g: Graph, o: LayoutOptions) -> None:
    # The channels of the gaps: the groups of the steps across the flow
    # sharing an end, overlapping groups in different channels ordered
    # against the crossings, the cycles broken by the depth-first search,
    # the channel the longest path (the orthogonal router of ELK Layered).
    g.channels = [0] * (g.last + 2)
    g.gaps = [o.layer_gap] * (g.last + 2)
    for layer in range(1, g.last):
        steps: List[_Step] = []
        for k, e in enumerate(g.edges):
            for i in range(len(e.chain) - 1):
                if g.vertices[e.chain[i]].layer != layer or \
                        g.vertices[e.chain[i + 1]].kind == VERTEX_VIRTUAL:
                    continue
                a = _chain_cross(g, e, i)
                b = _chain_cross(g, e, i + 1)
                if abs(a - b) > COORD_EPS:
                    steps.append(_Step(k, i, a, b))
        if not steps:
            continue
        parent = list(range(len(steps)))
        for s, st in enumerate(steps):
            es = g.edges[st.edge]
            s0, s1 = es.chain[st.step], es.chain[st.step + 1]
            for u in range(s + 1, len(steps)):
                su = steps[u]
                eu = g.edges[su.edge]
                u0, u1 = eu.chain[su.step], eu.chain[su.step + 1]
                start = s0 == u0 and \
                    g.vertices[s0].kind == VERTEX_REAL and \
                    abs(st.a - su.a) <= COORD_EPS
                end = s1 == u1 and g.vertices[s1].kind == VERTEX_REAL and \
                    abs(st.b - su.b) <= COORD_EPS
                if start or end:
                    ru = _group_root(parent, u)
                    parent[ru] = _group_root(parent, s)
        gindex = [-1] * len(steps)
        groups: List[_ChannelGroup] = []
        for s, st in enumerate(steps):
            r = _group_root(parent, s)
            lo = st.a if st.a < st.b else st.b
            hi = st.b if st.a < st.b else st.a
            if gindex[r] < 0:
                gindex[r] = len(groups)
                groups.append(_ChannelGroup(lo, hi))
            cg = groups[gindex[r]]
            if lo < cg.lo:
                cg.lo = lo
            if hi > cg.hi:
                cg.hi = hi
            cg.starts.append(st.a)
            cg.ends.append(st.b)
            st.group = gindex[r]
        n = len(groups)
        after: List[List[int]] = [[] for _ in range(n)]
        for s in range(n):
            for t in range(s + 1, n):
                if groups[s].lo > groups[t].hi + COORD_EPS or \
                        groups[t].lo > groups[s].hi + COORD_EPS:
                    continue
                if _channel_cost(groups[s], groups[t]) <= \
                        _channel_cost(groups[t], groups[s]):
                    after[s].append(t)
                else:
                    after[t].append(s)
        # the cycles: a back arc of the depth-first search is reversed
        dag: List[List[int]] = [[] for _ in range(n)]
        state = [0] * n
        for r in range(n):
            if state[r]:
                continue
            state[r] = 1
            stack = [[r, 0]]
            while stack:
                u = stack[-1][0]
                if stack[-1][1] < len(after[u]):
                    v = after[u][stack[-1][1]]
                    stack[-1][1] += 1
                    if state[v] == 1:
                        dag[v].append(u)
                    else:
                        dag[u].append(v)
                        if state[v] == 0:
                            state[v] = 1
                            stack.append([v, 0])
                else:
                    state[u] = 2
                    stack.pop()
        # the channels: the longest path from the layer before
        indegree = [0] * n
        level = [1] * n
        for u in range(n):
            for v in dag[u]:
                indegree[v] += 1
        order = [u for u in range(n) if not indegree[u]]
        i = 0
        while i < len(order):
            u = order[i]
            for v in dag[u]:
                if level[u] + 1 > level[v]:
                    level[v] = level[u] + 1
                indegree[v] -= 1
                if indegree[v] == 0:
                    order.append(v)
            i += 1
        channels = max(level) if level else 0
        for st in steps:
            g.edges[st.edge].channel[st.step] = level[st.group]
        g.channels[layer] = channels
        if (channels + 1) * CHANNEL_GAP > g.gaps[layer]:
            g.gaps[layer] = (channels + 1) * CHANNEL_GAP


def _gap_after(g: Graph, o: LayoutOptions, layer: int) -> float:
    # The gap after a layer: the layer gap, wider for the channels.
    return g.gaps[layer] if 0 <= layer < len(g.gaps) else o.layer_gap


def _priority_passes(g: Graph, o: LayoutOptions) -> None:
    t = (g.last + 1) // 2
    for layer in range(1, g.last + 1):
        _priority_pass(g, o, layer, True)
    for layer in range(g.last - 1, 0, -1):
        _priority_pass(g, o, layer, False)
    for layer in range(1 if t < 1 else t, g.last + 1):
        _priority_pass(g, o, layer, True)


def _assign_coordinates(g: Graph, o: LayoutOptions) -> None:
    start = scale = first_flow = first_centre = 0.0
    first = -1
    for layer in range(1, g.last + 1):
        _pack_layer(g, o, layer)
    _priority_passes(g, o)
    if not g.pinned and g.pull > 0.0:
        # the arrange: the passes again, the seeded vertices pulled
        scale = _pull_targets(g, o, _band_centres(g, o))
        if scale > 0.0:
            for layer in range(1, g.last + 1):
                _pack_layer(g, o, layer)
            _priority_passes(g, o)
    if g.orthogonal:
        _ports(g)
        _straighten(g, o)
        _channels(g, o)
    if g.pinned:
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
        at = start + band / 2.0
        flow = _seed_flow(g, layer) if scale > 0.0 else None
        if flow is not None:
            # the arrange: a seeded band at its seed place, never closer
            # than the layer gap to the band before
            if first < 0:
                first = layer
                first_flow = flow
                first_centre = at
            else:
                target = first_centre + scale * (flow - first_flow)
                pull = g.pull if g.pull < 1.0 else 1.0
                if target > at:
                    at += pull * (target - at)
        for w in nodes:
            g.vertices[w].flow = at
        start = at + band / 2.0 + _gap_after(g, o, layer)
    g.vertices[g.entry].flow = 0.0
    gap = _gap_after(g, o, g.last)
    g.vertices[g.exit].flow = start - gap if start > gap else 0.0


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


def _bands(g: Graph) -> Tuple[List[float], List[float]]:
    # The orthogonal routing: the extents of the bands along the flow.
    any_ = [False] * (g.last + 2)
    start = [0.0] * (g.last + 2)
    end = [0.0] * (g.last + 2)
    for vx in g.vertices:
        a = vx.flow - vx.flow_size / 2.0
        b = vx.flow + vx.flow_size / 2.0
        if vx.kind == VERTEX_VIRTUAL or vx.layer < 1 or vx.layer > g.last:
            continue
        if not any_[vx.layer] or a < start[vx.layer]:
            start[vx.layer] = a
        if not any_[vx.layer] or b > end[vx.layer]:
            end[vx.layer] = b
        any_[vx.layer] = True
    return start, end


def _orthogonal_piece(g: Graph, e: LayoutEdge, band_start: List[float],
                      band_end: List[float], piece: Piece) -> None:
    # The piece of an edge in the layout direction: the port on the side of
    # a real end, the turns of a step in its channel.
    m = len(e.chain) - 1
    for i in range(m + 1):
        v = g.vertices[e.chain[i]]
        dummy = v.kind not in (VERTEX_REAL, VERTEX_VIRTUAL)
        if i == 1 and dummy and \
                g.vertices[e.chain[0]].kind == VERTEX_VIRTUAL:
            # a run from the outside crosses the band of its dummy whole:
            # its label beside it, the join before
            piece.bends.append(Point(*_to_doc(g.direction,
                                              band_start[v.layer],
                                              _chain_cross(g, e, i))))
            piece.boxes.append(None)
        if v.kind == VERTEX_REAL and (i == 0 or i == m):
            fs, _ = _node_frame(g, v)
            piece.bends.append(Point(*_to_doc(
                g.direction, v.flow + fs / 2.0 if i == 0
                else v.flow - fs / 2.0, _chain_cross(g, e, i))))
            piece.boxes.append(v.node)
        if i < m and i < len(e.channel) and e.channel[i] > 0:
            layer = v.layer
            lo = band_end[layer]
            room = band_start[layer + 1] - band_end[layer]
            if room < 0.0:
                room = 0.0
            f = lo + e.channel[i] * room / (g.channels[layer] + 1)
            piece.bends.append(Point(*_to_doc(g.direction, f,
                                              _chain_cross(g, e, i))))
            piece.boxes.append(None)
            piece.bends.append(Point(*_to_doc(g.direction, f,
                                              _chain_cross(g, e, i + 1))))
            piece.boxes.append(None)
        if i + 1 == m and i >= 1 and dummy and \
                g.vertices[e.chain[m]].kind == VERTEX_VIRTUAL:
            # a run to the outside likewise, the join after
            piece.bends.append(Point(*_to_doc(g.direction, band_end[v.layer],
                                              _chain_cross(g, e, i))))
            piece.boxes.append(None)


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
    band_start: List[float] = []
    band_end: List[float] = []
    if g.orthogonal:
        band_start, band_end = _bands(g)
    for e in g.edges:
        piece = Piece(e.edge)
        if g.orthogonal:
            _orthogonal_piece(g, e, band_start, band_end, piece)
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
            if g.orthogonal:
                continue
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
            piece.boxes.reverse()
        c.pieces.append(piece)


def _graph_prepare(ctx: Context, ci: int) -> Graph:
    """P2 - P5: the direction-independent phases."""
    g = _build_graph(ctx, ci)
    for vx in g.vertices:
        if not vx.seed:
            continue
        if g.direction == FLOW_DOWN:
            vx.seed_flow, vx.seed_cross = vx.seed_y, vx.seed_x
            vx.seed_flow_size = vx.seed_h
        else:
            vx.seed_flow, vx.seed_cross = vx.seed_x, vx.seed_y
            vx.seed_flow_size = vx.seed_w
    if g.seeded:
        # a new edge inside one band keeps a straight line
        _seed_bands(g)
        g.edges = [e for e in g.edges
                   if not (e.seeded_ends and
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
                vx.seed_flow_size = vx.seed_h
            else:
                vx.seed_flow, vx.seed_cross = vx.seed_x, vx.seed_y
                vx.seed_flow_size = vx.seed_w
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
    if g.pinned:
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
    elif ctx.opts.mode == LAYOUT_ADAPTIVE and not ctx.seeded:
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
    if node.role == ROLE_CHOICE:
        # a choice is a square: the choice size, else the larger side of
        # its preset or its seed
        w, h = _at_least_seed(
            ctx, node,
            node.min_rect.width if node.min_rect is not None
            else ctx.opts.choice_size,
            node.min_rect.height if node.min_rect is not None
            else ctx.opts.choice_size)
        side = w if w > h else h
        node.rect = Rect(0.0, 0.0, side, side)
        return
    w, h = _at_least_seed(
        ctx, node,
        node.min_rect.width if node.min_rect is not None
        else ctx.opts.node_width,
        node.min_rect.height if node.min_rect is not None
        else ctx.opts.node_height)
    node.rect = Rect(0.0, 0.0, w, h)


def _fit(ctx: Context, node: Optional[Node], cw: float,
         ch: float) -> Tuple[float, float, float, float]:
    """P8: the container rect around the content, the title on top."""
    o = ctx.opts
    has_min = node is not None and node.min_rect is not None
    min_w = node.min_rect.width if has_min else 0.0    # type: ignore
    min_h = node.min_rect.height if has_min else 0.0   # type: ignore
    title = node.min_rect.height if has_min else o.padding  # type: ignore
    if cw <= 0.0 and ch <= 0.0:
        width, height = _at_least_seed(
            ctx, node, min_w if min_w > o.node_width else o.node_width,
            min_h if min_h > o.node_height else o.node_height)
        return width, height, o.padding, title
    width = cw + 2 * o.padding
    if min_w > width:
        width = min_w
    height = title + o.padding + ch + o.padding
    width, height = _at_least_seed(ctx, node, width, height)
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
    if not ctx.pinned or c.kind != CONTAINER_REGIONS:
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
    if ctx.opts.mode == LAYOUT_ADAPTIVE and not ctx.seeded:
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
        if ctx.pinned and p.point is not None:
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
    if ctx.pinned:
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
    a.role = box.role       # a choice ends at its tips
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
        project_edge_to_borders(e, True)
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
    for i, b in enumerate(piece.bends):
        box = piece.boxes[i] if i < len(piece.boxes) else None
        wps.append(_Waypoint(False, box, Point(b.x + ox, b.y + oy), False))


# The orthogonal routing: the joins in axis runs.
ALIGNED = 0.01      # two points this close on an axis are aligned
BEND = 40.0         # the length a turn of a detour costs


def _side(box: Optional[Node], p: Point) -> int:
    # The side of its box a point lies on: -1 none, 0 left, 1 right, 2 top,
    # 3 bottom.
    if box is None or box.rect is None:
        return -1
    r = box.rect
    d = [abs(p.x - r.x), abs(p.x - r.x - r.width), abs(p.y - r.y),
         abs(p.y - r.y - r.height)]
    best = 0
    for k in range(1, 4):
        if d[k] < d[best]:
            best = k
    return -1 if d[best] > ALIGNED else best


def _side_axis(side: int) -> int:
    return 0 if side < 0 else (1 if side < 2 else 2)


def _rect_side(p: Point, r: Rect) -> int:
    # 1 strictly inside the rect, -1 strictly outside, 0 on its border.
    e = ALIGNED
    if p.x < r.x - e or p.x > r.x + r.width + e or p.y < r.y - e or \
            p.y > r.y + r.height + e:
        return -1
    if r.x + e < p.x < r.x + r.width - e and \
            r.y + e < p.y < r.y + r.height - e:
        return 1
    return 0


def _run_hits(a: Point, b: Point, box: Optional[Node]) -> bool:
    # An axis run crosses the border of a box or lies along it.
    e = ALIGNED
    r = box.rect if box is not None else None
    if r is None:
        return False
    sa = _rect_side(a, r)
    sb = _rect_side(b, r)
    if sa * sb < 0:
        return True
    if abs(a.y - b.y) <= e:
        x0, x1 = (a.x, b.x) if a.x < b.x else (b.x, a.x)
        if x1 <= r.x + e or x0 >= r.x + r.width - e:
            return False
        if abs(a.y - r.y) <= e or abs(a.y - r.y - r.height) <= e:
            return True
        return sa < 0 and sb < 0 and r.y < a.y < r.y + r.height
    if abs(a.x - b.x) <= e:
        y0, y1 = (a.y, b.y) if a.y < b.y else (b.y, a.y)
        if y1 <= r.y + e or y0 >= r.y + r.height - e:
            return False
        if abs(a.x - r.x) <= e or abs(a.x - r.x - r.width) <= e:
            return True
        return sa < 0 and sb < 0 and r.x < a.x < r.x + r.width
    return False


def _stub(ctx: Context, box: Node, side: int, p: Point,
          other: Point) -> Point:
    # A padding half across the side, inward when the other point is inside.
    assert box.rect is not None
    d = ctx.opts.padding / 2.0
    if _rect_side(other, box.rect) > 0:
        d = -d
    s = Point(p.x, p.y)
    if side == 0:
        s.x -= d
    elif side == 1:
        s.x += d
    elif side == 2:
        s.y -= d
    else:
        s.y += d
    return s


def _obstacles(nodes: List[Node], out: List[Node]) -> None:
    # The boxes a route keeps off: the comments and the regions aside.
    for n in nodes:
        if n.rect is not None and n.type != REGION and \
                not node_is_comment(n):
            out.append(n)
        if n.children:
            _obstacles(n.children, out)


def _run_clear(a: Point, b: Point, boxes: List[Node]) -> bool:
    return not any(_run_hits(a, b, box) for box in boxes)


def _path_clear(pa: Point, mid: List[Point], pc: Point,
                boxes: List[Node]) -> bool:
    prev = pa
    for nxt in mid + [pc]:
        if not _run_clear(prev, nxt, boxes):
            return False
        prev = nxt
    return True


def _unique(v: List[float]) -> List[float]:
    out: List[float] = []
    for x in sorted(v):
        if not out or x - out[-1] > ALIGNED:
            out.append(x)
    return out


def _nearest(v: List[float], x: float) -> int:
    best = 0
    for i in range(1, len(v)):
        if abs(v[i] - x) < abs(v[best] - x):
            best = i
    return best


def _detour(ctx: Context, pa: Point, pc: Point, axis: int,
            boxes: List[Node]) -> Optional[List[Point]]:
    # The shortest way in axis runs, a turn costing BEND, over the lines of
    # the ends and a padding half off the sides of the boxes.
    pad = ctx.opts.padding / 2.0
    xs = [pa.x, pc.x]
    ys = [pa.y, pc.y]
    for box in boxes:
        r = box.rect
        assert r is not None
        xs += [r.x - pad, r.x + r.width + pad]
        ys += [r.y - pad, r.y + r.height + pad]
    xs = _unique(xs)
    ys = _unique(ys)
    ny = len(ys)
    ia, ja = _nearest(xs, pa.x), _nearest(ys, pa.y)
    ic, jc = _nearest(xs, pc.x), _nearest(ys, pc.y)
    cost = [-1.0] * (len(xs) * ny * 2)
    from_ = [-1] * (len(xs) * ny * 2)
    queue: List[Tuple[float, int]] = []
    for d in (0, 1):
        if axis and axis - 1 != d:
            continue
        s = (ia * ny + ja) * 2 + d
        cost[s] = 0.0
        heapq.heappush(queue, (0.0, s))
    goal = -1
    while queue:
        c0, s = heapq.heappop(queue)
        d = s % 2
        i, j = (s // 2) // ny, (s // 2) % ny
        if c0 > cost[s]:
            continue
        if i == ic and j == jc:
            goal = s
            break
        for k in range(4):
            ni = i + (-1 if k == 0 else 1 if k == 1 else 0)
            nj = j + (-1 if k == 2 else 1 if k == 3 else 0)
            nd = 0 if k < 2 else 1
            if ni < 0 or nj < 0 or ni >= len(xs) or nj >= ny:
                continue
            a = Point(xs[i], ys[j])
            b = Point(xs[ni], ys[nj])
            if not _run_clear(a, b, boxes):
                continue
            c = c0 + abs(b.x - a.x) + abs(b.y - a.y) + \
                (BEND if nd != d else 0.0)
            ns = (ni * ny + nj) * 2 + nd
            if cost[ns] < 0.0 or c < cost[ns] - COORD_EPS:
                cost[ns] = c
                from_[ns] = s
                heapq.heappush(queue, (c, ns))
    if goal < 0:
        return None
    path: List[Point] = []
    s = goal
    while s >= 0:
        p = Point(xs[(s // 2) // ny], ys[(s // 2) % ny])
        if not path or abs(path[-1].x - p.x) > ALIGNED or \
                abs(path[-1].y - p.y) > ALIGNED:
            path.append(p)
        s = from_[s]
    path.reverse()
    return path[1:-1]


def _join(ctx: Context, a: Point, ba: Optional[Node], axis_a: int, c: Point,
          bc: Optional[Node], boxes: List[Node], q: List[Point],
          qb: List[Optional[Node]]) -> None:
    # The join of two points in axis runs: the stubs of the points on the
    # sides of their boxes, then the first way clear of the boxes - a turn
    # (the way the first point goes preferred), a detour, else a step
    # halfway.
    e = ALIGNED
    side_a = _side(ba, a)
    side_c = _side(bc, c)
    need_c = _side_axis(side_c)
    aligned_x = abs(a.y - c.y) <= e
    aligned_y = abs(a.x - c.x) <= e
    if side_a >= 0:
        axis_a = _side_axis(side_a)
    if ((aligned_x and axis_a in (0, 1) and need_c in (0, 1)) or
            (aligned_y and axis_a in (0, 2) and need_c in (0, 2))) and \
            _run_clear(a, c, boxes):
        q.append(c)
        qb.append(bc)
        return
    pa = _stub(ctx, ba, side_a, a, c) if side_a >= 0 and ba is not None \
        else a
    pc = _stub(ctx, bc, side_c, c, a) if side_c >= 0 and bc is not None \
        else c
    first = 1 if axis_a == 2 or (not axis_a and (
        need_c == 1 or (not need_c and abs(c.y - a.y) > abs(c.x - a.x)))) \
        else 0
    best: Optional[List[Point]] = None
    for j in range(2):
        k = first if j == 0 else 1 - first
        t = Point(pc.x, pa.y) if k == 0 else Point(pa.x, pc.y)
        if _path_clear(pa, [t], pc, boxes):
            best = [t]
            break
    if best is None:
        best = _detour(ctx, pa, pc, axis_a, boxes)
    if best is None:
        if first == 0:
            mx = (pa.x + pc.x) / 2.0
            best = [Point(mx, pa.y), Point(mx, pc.y)]
        else:
            my = (pa.y + pc.y) / 2.0
            best = [Point(pa.x, my), Point(pc.x, my)]
    if side_a >= 0:
        q.append(pa)
        qb.append(None)
    for t in best:
        q.append(t)
        qb.append(None)
    if side_c >= 0:
        q.append(pc)
        qb.append(None)
    q.append(c)
    qb.append(bc)


def _orthogonal_route(ctx: Context, e: Edge, wps: List['_Waypoint']) -> None:
    # The route made orthogonal: the joins of the pieces, the containers and
    # the ends in axis runs, the repeated and the straight-through points
    # dropped.
    if e.source_point is None or e.target_point is None:
        return
    boxes: List[Node] = []
    _obstacles(ctx.tree.nodes, boxes)
    p = [e.source_point] + [w.p for w in wps] + [e.target_point]
    b: List[Optional[Node]] = [e.source] + [w.box for w in wps] + \
        [e.target]
    q: List[Point] = []
    qb: List[Optional[Node]] = []
    # the repeated points: the inner one kept (exact, not through float)
    for i, pt in enumerate(p):
        if q and abs(q[-1].x - pt.x) <= ALIGNED and \
                abs(q[-1].y - pt.y) <= ALIGNED:
            if len(q) == 1 and i + 1 < len(p):
                q[-1] = pt
            if qb[-1] is None:
                qb[-1] = b[i]
            continue
        q.append(pt)
        qb.append(b[i])
    p, b = q, qb
    q = [p[0]]
    qb = [b[0]]
    for i in range(1, len(p)):
        a = q[-1]
        axis = 0
        if len(q) > 1:
            z = q[-2]
            axis = 1 if abs(z.y - a.y) <= ALIGNED else 2
        _join(ctx, a, qb[-1], axis, p[i], b[i], boxes, q, qb)
    # the points a straight run passes through
    p = []
    for i, pt in enumerate(q):
        if p and i + 1 < len(q):
            z = p[-1]
            n = q[i + 1]
            along_y = abs(z.x - pt.x) <= ALIGNED and abs(pt.x - n.x) <= ALIGNED
            along_x = abs(z.y - pt.y) <= ALIGNED and abs(pt.y - n.y) <= ALIGNED
            if along_x or along_y:
                continue
        p.append(pt)
    e.source_point = Point(p[0].x, p[0].y)
    e.target_point = Point(p[-1].x, p[-1].y)
    e.polyline = [Point(pt.x, pt.y) for pt in p[1:-1]] or None


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
            project_edge_to_borders(e, True)
    else:
        p = _border_crossing(e.source, wps[0].p.x, wps[0].p.y)
        e.source_point = (p if p is not None else sc).copy()
        p = _border_crossing(e.target, wps[-1].p.x, wps[-1].p.y)
        e.target_point = (p if p is not None else tc).copy()
        e.polyline = [w.p.copy() for w in wps]
    if ctx.opts.routing == ROUTING_ORTHOGONAL:
        _orthogonal_route(ctx, e, wps)
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
            b = e.polyline[0] if e.polyline else e.target_point
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
        if ctx.pinned and e not in ctx.routed:
            continue
        group = [f for f in ctx.tree.edges
                 if _straight(f) and _same_pair(e, f) and
                 (not ctx.pinned or f in ctx.routed)]
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
    if not ctx.pinned or e not in ctx.edge_seeds:
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
        if ctx.pinned:
            if _edge_kept(ctx, e) and _fit_route(e):
                continue
            _drop_edge_geometry(e)
            ctx.routed.add(e)
        if e.source is e.target:
            _route_loop(ctx, e)
            continue
        _route_edge(ctx, e)
    # the ports spread the orthogonal routes already
    if ctx.opts.routing != ROUTING_ORTHOGONAL:
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
    w, h = _at_least_seed(
        ctx, comment,
        comment.min_rect.width if comment.min_rect is not None
        else o.node_width,
        comment.min_rect.height if comment.min_rect is not None
        else o.node_height)
    r = Rect(0.0, 0.0, w, h)
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


def _attach_links(ctx: Context) -> None:
    # The comment links once the comments are placed: the update keeps a
    # drawn link whose ends stayed (or moved alike) and whose commented edge
    # was not routed again, and fills only the missing ends.
    from .transform import attach_link
    for e in ctx.tree.edges:
        if e.source is None or e.target is None or \
                not node_is_comment(e.source):
            continue
        if ctx.pinned and not (_edge_kept(ctx, e) and
                               (e.target_edge is None or
                                e.target_edge not in ctx.routed)):
            _drop_edge_geometry(e)
        attach_link(e)


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


def _collect_sizes(ctx: Context, nodes: List[Node]) -> None:
    # The arrange: the seed rects become the minimum sizes.
    for n in nodes:
        if n.rect is not None:
            ctx.seed_sizes[n] = n.rect.copy()
        if n.children:
            _collect_sizes(ctx, n.children)


def _tree_pass(tree: Tree, reconstruct_sm: bool, opts: LayoutOptions,
               start: int, mode: int) -> Tuple[float, float]:
    from .transform import grow_sm_border
    ctx = Context(tree, opts, start, reconstruct_sm, mode)
    root = tree.nodes[0] if len(tree.nodes) == 1 and \
        tree.nodes[0].type == TREE else None
    ctx.sm_had_rect = root is not None and root.rect is not None
    if ctx.seeded:
        _collect_seeds(ctx, tree.nodes)
    if ctx.seeded and not ctx.pinned:
        _collect_sizes(ctx, tree.nodes)
    if ctx.pinned:
        for e in tree.edges:
            if e.source_point is not None or e.target_point is not None or \
                    e.polyline is not None or e.label_point is not None:
                ctx.edge_seeds.add(e)
    else:
        # the full layout and the arrange rebuild the geometry
        clean_tree_geometry(tree.nodes)
        for e in tree.edges:
            e.source_point = e.target_point = e.label_point = None
            e.polyline = None
    _collect(ctx, root, 0)
    _seed_edges(ctx)
    if ctx.seeded:
        _infer_directions(ctx)
    _container(ctx, 0)
    _route_edges(ctx)
    _place_comments(ctx, tree.nodes)
    _attach_links(ctx)
    grow_sm_border(tree)
    return _final_shape(ctx)


def layout_tree(tree: Tree, reconstruct_sm: bool, opts: LayoutOptions,
                mode: int) -> None:
    """Lay a tree out; the adaptive mode keeps the better of two starts."""
    if mode != REBUILD_FULL or opts.mode != LAYOUT_ADAPTIVE:
        _tree_pass(tree, reconstruct_sm, opts, opts.direction, mode)
        return
    wr, hr = _tree_pass(tree, reconstruct_sm, opts, FLOW_RIGHT, REBUILD_FULL)
    wd, hd = _tree_pass(tree, reconstruct_sm, opts, FLOW_DOWN, REBUILD_FULL)
    better = _shape_better(wr, hr, wd, hd, opts.aspect)
    if better == 0 or (better < 0 and opts.direction == FLOW_RIGHT):
        _tree_pass(tree, reconstruct_sm, opts, FLOW_RIGHT, REBUILD_FULL)


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
