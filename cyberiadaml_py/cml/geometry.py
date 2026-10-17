# -----------------------------------------------------------------------------
# The Cyberiada State Machine Python 3 Library
#
# The geometry values of the CyberiadaML interface
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
"""The geometry values: Point, Rect and Polyline."""
import math
from typing import Iterable, List, Optional


def number(value: float) -> str:
    """Return a coordinate as the C++ stream prints it (6 digits)."""
    return format(value, 'g')


def round_half_away(value: float) -> float:
    """Return the value rounded as the C library rounds it."""
    return math.copysign(math.floor(abs(value) + 0.5), value)


class Point:
    """A point; Point() is not valid."""

    def __init__(self, x: Optional[float] = None,
                 y: Optional[float] = None) -> None:
        self.valid = x is not None and y is not None
        self.x = float(x) if x is not None else 0.0
        self.y = float(y) if y is not None else 0.0

    def round(self) -> None:
        self.x, self.y = round_half_away(self.x), round_half_away(self.y)

    def copy(self) -> 'Point':
        return Point(self.x, self.y) if self.valid else Point()

    def __repr__(self) -> str:
        if not self.valid:
            return '()'
        return '(%s; %s)' % (number(self.x), number(self.y))


class Rect:
    """A rect; Rect() is not valid."""

    def __init__(self, x: Optional[float] = None, y: Optional[float] = None,
                 width: Optional[float] = None,
                 height: Optional[float] = None) -> None:
        self.valid = None not in (x, y, width, height)
        self.x = float(x) if x is not None else 0.0
        self.y = float(y) if y is not None else 0.0
        self.width = float(width) if width is not None else 0.0
        self.height = float(height) if height is not None else 0.0

    def round(self) -> None:
        self.x, self.y = round_half_away(self.x), round_half_away(self.y)
        self.width = round_half_away(self.width)
        self.height = round_half_away(self.height)

    def copy(self) -> 'Rect':
        if not self.valid:
            return Rect()
        return Rect(self.x, self.y, self.width, self.height)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Rect):
            return NotImplemented
        return (self.valid, self.x, self.y, self.width, self.height) == \
            (other.valid, other.x, other.y, other.width, other.height)

    def __ne__(self, other: object) -> bool:
        result = self.__eq__(other)
        return result if result is NotImplemented else not result

    __hash__ = None  # type: ignore[assignment]

    def __repr__(self) -> str:
        if not self.valid:
            return '()'
        return '(%s; %s; %s; %s)' % (number(self.x), number(self.y),
                                     number(self.width), number(self.height))


class Polyline:
    """A list of points; an item read is a copy."""

    def __init__(self, points: Optional[Iterable[Point]] = None) -> None:
        self._points: List[Point] = [p.copy() for p in points or []]

    def append(self, point: Point) -> None:
        self._points.append(point.copy())

    def round(self) -> None:
        for point in self._points:
            point.round()

    def copy(self) -> 'Polyline':
        return Polyline(self._points)

    def __getitem__(self, index: int) -> Point:
        if index < 0:
            raise TypeError('a non-negative index is expected')
        return self._points[index].copy()

    def __setitem__(self, index: int, point: Point) -> None:
        self._points[index] = point.copy()

    def __iter__(self):
        return iter([p.copy() for p in self._points])

    def __len__(self) -> int:
        return len(self._points)

    def __repr__(self) -> str:
        return '[ %s ]' % ', '.join(repr(p) for p in self._points)
