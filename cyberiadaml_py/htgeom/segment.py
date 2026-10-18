# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The segment and rect intersection of the border projection
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
"""The segment/rect intersection the border projection needs.

The arithmetic of the homogeneous coordinates the C++ library computes it
with: lines are the cross products of points, normalised by hypot; the
crossing is the cross product of the lines.
"""
import math
from typing import List, Optional, Tuple

from .types import GeometryError, TRANSFORM_ERROR

NULL_DISTANCE = 1e-10       # equal points, a point on a segment
NULL_ORTHO_DISTANCE = 1e-14  # a degenerate rect
NULL_ANGLE = 0.001          # parallel lines, radians
NULL_DENOM = 1e-10
EPSILON = 2.220446049250313e-16

Vec = Tuple[float, float, float]


def _cross(a: Vec, b: Vec) -> Vec:
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _distance(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _equal(a: Tuple[float, float], b: Tuple[float, float]) -> bool:
    return _distance(a, b) < NULL_DISTANCE


def _line(p: Tuple[float, float], q: Tuple[float, float]) -> Vec:
    if _equal(p, q):
        raise GeometryError(TRANSFORM_ERROR, 'points are identical')
    a, b, c = _cross((p[0], p[1], 1.0), (q[0], q[1], 1.0))
    norm = math.hypot(a, b)
    if norm <= EPSILON:
        raise GeometryError(TRANSFORM_ERROR, 'unable to normalize line')
    a, b, c = a / norm, b / norm, c / norm
    if a < 0.0:
        a, b, c = -a, -b, -c
    if abs(a) < NULL_DENOM and b < 0:
        b, c = -b, -c
    return (a, b, c)


def _angle(l1: Vec, l2: Vec) -> float:
    res = l1[0] * l2[0] + l1[1] * l2[1]
    res /= math.sqrt((l1[0] * l1[0] + l1[1] * l1[1]) *
                     (l2[0] * l2[0] + l2[1] * l2[1]))
    return math.acos(min(abs(res), 1.0))


class Segment:
    """An unoriented segment: the ends sorted by x, then by y."""

    def __init__(self, p: Tuple[float, float],
                 q: Tuple[float, float]) -> None:
        if _equal(p, q):
            raise GeometryError(TRANSFORM_ERROR,
                                'a segment with two identical points')
        self.p1, self.p2 = (p, q) if p < q else (q, p)

    def length(self) -> float:
        return _distance(self.p1, self.p2)

    def intersects(self, other: 'Segment') -> Optional[Tuple[float, float]]:
        if _equal(self.p1, other.p1) and _equal(self.p2, other.p2):
            return None
        l1 = _line(self.p1, self.p2)
        l2 = _line(other.p1, other.p2)
        if _angle(l1, l2) < NULL_ANGLE:
            return None
        w = _cross(l1, l2)
        point = (w[0] / w[2], w[1] / w[2])
        if abs(_distance(self.p1, point) + _distance(self.p2, point) -
               self.length()) < NULL_DISTANCE and \
                abs(_distance(other.p1, point) +
                    _distance(other.p2, point) - other.length()) < \
                NULL_DISTANCE:
            return point
        return None


def rect_corners(x1: float, y1: float, x2: float,
                 y2: float) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    """Return the normalised corners; a degenerate rect is an error."""
    if abs(x1 - x2) < NULL_ORTHO_DISTANCE or \
            abs(y1 - y2) < NULL_ORTHO_DISTANCE:
        raise GeometryError(TRANSFORM_ERROR,
                            'a coordinate of the 2 points is identical, does '
                            'not define a rectangle')
    return (min(x1, x2), min(y1, y2)), (max(x1, x2), max(y1, y2))


def segment_rect_points(p: Tuple[float, float], q: Tuple[float, float],
                        x: float, y: float, w: float,
                        h: float) -> List[Tuple[float, float]]:
    """Return the sorted crossings of the segment pq and a rect."""
    r1, r2 = rect_corners(x, y, x + w, y + h)
    corners = [r1, (r1[0], r2[1]), r2, (r2[0], r1[1])]
    segment = Segment(p, q)
    result: List[Tuple[float, float]] = []
    for k in range(4):
        side = Segment(corners[k], corners[(k + 1) % 4])
        point = side.intersects(segment)
        if point is None:
            continue
        if len(result) == 1 and _equal(result[0], point):
            continue
        result.append(point)
        if len(result) == 2:
            break
    return sorted(result)
