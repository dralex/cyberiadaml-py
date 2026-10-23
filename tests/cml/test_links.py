# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The comment links of the htgeom port
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
"""The comment links of the htgeom port beside the C++ tests 49 and 50."""
from cyberiadaml_py.htgeom import types as ht
from cyberiadaml_py.htgeom.transform import attach_link


def _node(type_, id_, rect):
    node = ht.Node(type_, id_)
    node.rect = ht.Rect(*rect)
    return node


def _edges():
    a = _node(ht.SIMPLE, 'a', (100, 100, 200, 100))
    b = _node(ht.SIMPLE, 'b', (500, 100, 200, 100))
    c = _node(ht.COMMENT, 'c', (300, 400, 100, 40))
    ab = ht.Edge('e-a-b', 'a', 'b')
    ab.source, ab.target = a, b
    ab.source_point, ab.target_point = ht.Point(300, 150), ht.Point(500, 150)
    link = ht.Edge('l-c-ab', 'c', 'a')
    link.source, link.target = c, a
    link.type = ht.EDGE_LINK
    link.target_edge_id, link.target_edge = 'e-a-b', ab
    return ab, link


def test_link_to_transition_on_its_path():
    _, link = _edges()
    attach_link(link)
    assert (link.target_point.x, link.target_point.y) == (350, 150)
    assert (link.source_point.x, link.source_point.y) == (350, 400)


def test_link_foot_beside_the_label():
    ab, link = _edges()
    ab.label_rect = ht.Rect(320, 140, 60, 20)
    attach_link(link)
    assert (link.target_point.x, link.target_point.y) == (380, 150)


def test_chunk_link_without_target_point():
    _, link = _edges()
    link.type = ht.EDGE_CHUNK_LINK
    link.target_edge = None
    link.target_point = ht.Point(10, 10)
    attach_link(link)
    assert link.target_point is None and link.source_point is not None


def test_stored_ends_kept():
    _, link = _edges()
    link.source_point = ht.Point(310, 400)
    link.target_point = ht.Point(320, 150)
    attach_link(link)
    assert (link.source_point.x, link.target_point.x) == (310, 320)
